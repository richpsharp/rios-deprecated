"""This file contains core algorithmic functionality of the Water Funds
Prioritizer."""

import logging
import json
import os
import csv
import shutil
import math

from osgeo import gdal
import scipy.ndimage
import numpy

import pygeoprocessing.geoprocessing

LOGGER = logging.getLogger('rios.porter_core')

def linear_interpolate(dict_a, dict_b, parameter):
    """Creates a dictionary elements that are pairwise interpolated
        between dict_a and dict_b by amount parameter

        dict_a, dict_b - dictionaries with identical keys that may have floating
            point values
        parameter - float between 0.0 and 1.0 where 0.0 is full weight to
            list_a and 1.0 is full weight to list_b

        returns dict of {
            'keya': interp(dict_a['keya'],dict_b['keyb'], parameter), ...}"""

    interpolated_output = {}
    for key in dict_a:
        a_val = dict_a[key]
        b_val = dict_b[key]
        try:
            interpolated_output[key] = a_val*(1.0-parameter)+b_val*parameter
        except TypeError:
            interpolated_output[key] = "CAN'T INTERPOLATE"
    return interpolated_output

def generate_combined_lulc(in_lucode, transition_code, activity_id, out_lucode):
    """Create a consistent lucode id based on the in, transition, and out

        in_lucode - an integer < 999
        transition_code - an integer < 9
        activity_id - an integer < 99
        out_lucode - an integer < 999

        returns a unique integer that cannot be created by any other
            combination of input values"""

    if in_lucode > 999:
        raise Exception(
            "generate_combined_lulc has in_lucode > 999 as: %s" % in_lucode)
    if transition_code > 9:
        raise Exception(
            "generate_combined_lulc has transition_code > 99 as: %s" %
            transition_code)
    if activity_id > 99:
        raise Exception(
            "generate_combined_lulc has activity_id > 99 as: %s" % activity_id)
    if out_lucode > 999:
        raise Exception(
            "generate_combined_lulc has out_lucode > 999 as: %s" % out_lucode)

    return (
        in_lucode * 10**6 + transition_code * 10**5 + activity_id * 10**3 +
        out_lucode)

def load_transition_types(transitions_uri):
    """Loads a transition .json file and returns a dictionary mapping
        transition ids to their types.

        transitions_uri - path to a .json file with the format

            {
                "modify_landscape_structure": "restoration", ... }


        returns a dictionary whose keys and values are found in the transitions
            json file"""

    transitions_file = open(transitions_uri)
    transitions_string = transitions_file.read()
    transition_dictionary = json.loads(transitions_string)
    return transition_dictionary

def load_lulc_transitions(lulc_transition_uri):
    """Loads a lulc transition type csv file and returns a list of lulc
        type/transition tuples

        lulc_transition_uri - path to a csv file with the format
           "Original LULC,Transition,...
           lulc_type_1, transiton_type_a, ...
           ...."

        returns a list of lulc transitoin tuples found lulc transitions file"""

    lulc_transition_file = open(lulc_transition_uri)
    #Chuck the first line, that's the csv header
    lulc_transition_file.readline()
    lulc_transition_list = []
    for line in lulc_transition_file:
        #Grab just the first two elements from the line, that'll be the lulc
        #and the transition type
        lulc, transition = line.split(',')[0:2]

        #Chuck it if there's no transition
        if transition == '':
            continue

        lulc_transition_list.append((lulc, transition))

    return lulc_transition_list

def load_lulc_properties(general_coefficients_uri, header_list):
    """Loads the landscape properties specified in the parameters
        and dumps them to a dictionary indexed by lulc id

        general_coefficients_uri - a path to a file of the form:

          "lulc name,lulc code,native veg....
           lulc_1,1,0,...
           lulc_2,2,1,...
          ..."

        header_list - a list of column headers in the general coeffients
            csv file that will be read in

        returns a dictionary indexed by lulc codes to a list whose values
            relate to and are in the same order as header_list"""


    with open(general_coefficients_uri, 'rU') as f:
        reader = csv.reader(f)
        column_headers = reader.next()
        column_headers = [x.lower() for x in column_headers]
        lucode_index = column_headers.index('lulc_general')

        #This will be a list of property indexes we can use to index the
        #correct values in the rows we read from the csv in the next step
        #it'll look something like [3, 4, 5, 8, 9]
        properties_index = map(lambda x: column_headers.index(x), header_list)

        lulc_properties = {}
        for row in reader:
            #Create lucode index lookup.
            lu_code = int(row[lucode_index])

            #Make a list of tuples of the form ('Header name', header value)
            properties_list = [float(row[properties_index[i]])
                               for i in range(len(properties_index))]

            #Store that in the dictionary indexed by the lu code
            lulc_properties[lu_code] = properties_list

        return lulc_properties

def load_lulc_types(general_coefficients_uri):
    """Loads the general coeffients file just to get the lulc types

        general_coefficients_uri - a path to a file of the form:

          "lulc name,lulc code,native veg....
           lulc_1,1,0,...
           lulc_2,2,1,...
          ..."

        returns a list of dictionary with the keys 'name' and 'native'"""

    general_lulc_dict = pygeoprocessing.geoprocessing.get_lookup_from_csv(
        general_coefficients_uri, 'lucode')

    #This fixes an issue where the table might have blank inputs and create
    #string based keys and values.
    for key in general_lulc_dict.keys():
        try:
            _ = int(key)
        except ValueError:
            del general_lulc_dict[key]

    lulc_dict = {}
    for lucode in general_lulc_dict:
        #Grab just the first two elements from the line, that'll be the lulc
        #and the transition type
        lulc_dict[int(lucode)] = {
            'name': general_lulc_dict[lucode]['description'],
            'native': bool(general_lulc_dict[lucode]['native_veg'])
        }
    return lulc_dict


def find_native_transitions(
        lulc_dataset_uri, transition_dataset_uri, activity_dataset_uri,
        native_type_list, restoration_transition_list, native_distance_sigma,
        max_native_type_uri):
    """For each native type that has a restoration transition on it, find the
        "nearest" LULC type.  Returns a list of tuples (old lulc, new lulc,
        transition) that occur.

        lulc_dataset - a GDAL dataset containing land use codes
        transition_dataset - a GDAL dataset of same size and dimensions as
            lulc_dataset that contain transition codes
        activity_dataset - a GDAL dataset indicating which activity is
            implmeneted on each pixel
        native_type_list - a list of native lulc codes in lulc dataset
        restoration_transition_list - list of codes in transition dataset that
            are restoration types
        native_distance_stdev - the standard deviation of the gaussian kernel
            in pixels?

        returns [(old lulc code, native_lulc code, native_transition code), ...]
        """

    #for each native type
    #gaussian blur it on its own separate dataset
    lulc_dataset = gdal.Open(lulc_dataset_uri)
    lulc_band = lulc_dataset.GetRasterBand(1)
    lulc_nodata = lulc_band.GetNoDataValue()

    native_dataset_list = []

    native_array_position_to_id = {}

    for native_id in native_type_list:
        lulc_array = lulc_band.ReadAsArray()
        #Mask out the other native types
        lulc_array[lulc_array != native_id] = 0
        #make an output array of the correct precision
        native_reach_array = numpy.empty(lulc_array.shape, dtype=numpy.float)
        scipy.ndimage.gaussian_filter(
            lulc_array, native_distance_sigma, output=native_reach_array)

        #We'll use this later to determine which native array maps to its
        #original native LULC id
        native_array_position_to_id[len(native_dataset_list)] = native_id

        #Write out the native reach array for passing to vectorize rasters
        native_reach_uri = pygeoprocessing.geoprocessing.temporary_filename()
        native_reach_dataset = pygeoprocessing.geoprocessing.new_raster_from_base(
            lulc_dataset, native_reach_uri, 'GTiff', -1.0, gdal.GDT_Float32)
        native_band = native_reach_dataset.GetRasterBand(1)
        native_band.WriteArray(native_reach_array)

        native_dataset_list.append(native_reach_uri)

    #we're going to build up the native transition tuple set as a side effect
    #through vectorize rasters.  Not a good style, but the alternative
    native_transition_tuples = set()

    activity_nodata = pygeoprocessing.geoprocessing.get_nodata_from_uri(
        activity_dataset_uri)

    LOGGER.debug("native_array_position_to_id %s", native_array_position_to_id)

    def find_restoration_tuples(*args):
        original_lulc_array = args[0]
        transition_type_array = args[1]
        activity_type_array = args[2]
        native_type_array_list = args[3:]


        max_native_type_index_array = numpy.argmax(
            native_type_array_list, axis=0)

        tuple_stack = numpy.vstack((
            original_lulc_array.flatten(), transition_type_array.flatten(),
            activity_type_array.flatten(),
            max_native_type_index_array.flatten())).transpose()
        for original_lulc, transition_type, activity_type, \
                max_native_type_index \
                in set(tuple(p) for p in tuple_stack):
            if not any([
                    original_lulc == lulc_nodata,
                    transition_type not in restoration_transition_list,
                    activity_type == activity_nodata]):

                max_native_type_id = (
                    native_array_position_to_id[max_native_type_index])

                native_transition_tuples.add((
                    original_lulc, max_native_type_id, transition_type,
                    activity_type))

        #Using Godel numbering to account for the tuple, hopefully doesn't
        #overflow the 32 bit int
        #return (
        #    original_lulc_array * 2 + activity_type_array * 3 +
        #    transition_type_array * 5 + max_native_type_index_array * 7)

        max_native_lulc_ids = numpy.empty(max_native_type_index_array.shape)
        for index, lulc_id in native_array_position_to_id.iteritems():
            max_native_lulc_ids[max_native_type_index_array == index] = lulc_id
        return max_native_lulc_ids

    #restoration_tuple_uri = os.path.join(
    #    )pygeoprocessing.geoprocessing.temporary_filename()
    dataset_list = (
        [lulc_dataset_uri, transition_dataset_uri, activity_dataset_uri] +
        native_dataset_list)

    pixel_out = pygeoprocessing.geoprocessing.get_cell_size_from_uri(
        lulc_dataset_uri)
    pygeoprocessing.geoprocessing.vectorize_datasets(
        dataset_list, find_restoration_tuples, max_native_type_uri,
        gdal.GDT_Int32, -1, pixel_out, "intersection", vectorize_op=False)

    LOGGER.info('native transition tuples %s', native_transition_tuples)
    return native_transition_tuples


def find_agriculture_transitions(
    lulc_dataset_uri, transition_dataset_uri, agriculture_transition_list,
    activity_portfolio_dataset_uri):
    """For each native type that has a restoration transition on it, find the
        "nearest" LULC type.  Returns a list of tuples (old lulc, new lulc,
        transition) that occur.

        lulc_dataset - a GDAL dataset containing land use codes
        transition_dataset - a GDAL dataset of same size and dimensions as
            lulc_dataset that contain transition codes
        agriculture_transition_list - list of codes in transition dataset that
            are restoration types
        activity_portfolio_dataset_uri - uri to activity portfolio raster

        returns [(old lulc code, agriculture_transition code), ...]
        """

    agriculture_tuple_uri = pygeoprocessing.geoprocessing.temporary_filename()
    agriculture_transition_tuples = set()
    lulc_nodata = pygeoprocessing.geoprocessing.get_nodata_from_uri(
        lulc_dataset_uri)
    activity_nodata = pygeoprocessing.geoprocessing.get_nodata_from_uri(
        activity_portfolio_dataset_uri)
    cell_size = pygeoprocessing.geoprocessing.get_cell_size_from_uri(
        lulc_dataset_uri)

    activity_rat = pygeoprocessing.geoprocessing.get_rat_as_dictionary_uri(
        activity_portfolio_dataset_uri)
    activity_lookup = dict(
        [(raster_value, activity_rat['Activity'][raster_value])
         for raster_value in activity_rat['Value']])

    def find_agriculture_tuples(
            lulc_array, transition_type_array, activity_type_array):
        """searched for unique non-nodata combinations of lulc, transtion, and
            activity type and builds up a dictionary as a side effect if so"""
        #undefined_mask = (
        #    lulc == lulc_nodata |
        #    ~numpy.in1d(transition_type, agriculture_transition_list) |
        #    activity_type == activity_nodata)

        tuple_stack = numpy.vstack((
            lulc_array.flatten(), transition_type_array.flatten(),
            activity_type_array.flatten())).transpose()

        for lulc, transition_type, activity_type in set(tuple(p) for p in \
                tuple_stack):
            if all([lulc != lulc_nodata,
                    transition_type in agriculture_transition_list,
                    activity_type != activity_nodata]):
                agriculture_transition_tuples.add(
                    (lulc, transition_type, activity_lookup[activity_type]))

        #if any([lulc == lulc_nodata,
        #        transition_type not in agriculture_transition_list,
        #        activity_type == activity_nodata]):
        #    return -1

        #agriculture_transition_tuples.add(
        #    (lulc, transition_type, activity_lookup[activity_type]))

        #Using Godel numbering to account for the tuple, hopefully doesn't
        #overflow the 32 bit int
        return lulc_array * 2 + transition_type_array * 3

    dataset_list = [
        lulc_dataset_uri, transition_dataset_uri,
        activity_portfolio_dataset_uri]
    pygeoprocessing.geoprocessing.vectorize_datasets(
        dataset_list, find_agriculture_tuples, agriculture_tuple_uri,
        gdal.GDT_Int32, -1, cell_size, 'intersection', vectorize_op=False)

    return agriculture_transition_tuples

def build_native_transition_tuples(
        lulc_dataset_uri, transition_dataset_uri,
        activity_portfolio_dataset_uri, native_type_list,
        restoration_transition_list, transition_lookup,
        lulc_table, max_native_type_uri, default_transition_amount=None):
    """Build up rows of ('original lulc', 'transition name', 'new lulc')
        for potential usage in a table.

        lulc_dataset - gdal dataset of LULC codes used for searching types
        transition_dataset - gdal dataset of max transition types
        activity_portfolio_dataset - gdal dataset indicating what activities
           are selected on each pixel
        native_type_list - list of native types defined by RIOS
           format is a list of ints that correspond to the values
           in lulc_dataset [id1, id2, ...]
        restoration_transition_list - list of transitions that are defined by
            restoration types
        transition_lookup - a dictionary that indexed by transition id to
            textual description of transition
        max_native_type_uri - (output) a raster that maps the native type id
            to a single raster
        lulc_table - table of the form
            {lulcid: {'name': '..', 'native': True/False}, ...}
        default_transition_amount - (optional) if the user needs to have
           a default value appended to the tuple they can pass it in here


        returns all possible pairs of [('original lulc', 'new lulc',
            'transition name', default_transition_amount?), ...] from the
            input parameters"""

    native_distance_sigma = 5.0
    native_transition_ids = find_native_transitions(
        lulc_dataset_uri, transition_dataset_uri,
        activity_portfolio_dataset_uri, native_type_list,
        restoration_transition_list, native_distance_sigma, max_native_type_uri)

    #Load the activity rat which gives a dictionary of 'Value' 'Activity'
    #keys.  'Value' is pixel value list, 'Activity' is name of those pixels
    activity_rat = pygeoprocessing.geoprocessing.get_rat_as_dictionary_uri(
        activity_portfolio_dataset_uri)
    activity_lookup = dict(
        [(raster_value, activity_rat['Activity'][raster_value])
         for raster_value in activity_rat['Value']])

    native_transitions = [
        (lulc_table[pair[0]]['name'], transition_lookup[pair[2]],
         activity_lookup[pair[3]], lulc_table[pair[1]]['name'])
        for pair in native_transition_ids]

    if default_transition_amount != None:
        native_transitions = map(
            lambda x: x+(default_transition_amount,), native_transitions)

    return native_transitions

def write_csv(column_headers, rows, output_uri):
    """Given a list of column headers and contents, write to a csv file

        column_headers - a list of strings defining the column names
        rows - a list of lists where an inner list index corresponds
            to the column header in column_headers
        output_uri - the location to save the output .csv file

        returns nothing"""
    pass

def create_scenarios(
        workspace_dir, results_suffix, avoided_transition_lulc,
        protection_transition_percent, agriculture_table, restoration_table,
        activity_portfolio_dataset_uri, years_of_transition):
    """This function creates the original, transitioned, and unprotected scenarios
        for valuation.  Will write three .csv output tables of landcover types
        for a future valuation model runs.

        workspace_dir - the root directory that we can use to dump temporary
            files and load core RIOS files
        results_suffix - (optional) the possible suffix attached to the previous IPA
            run
        avoided_transition_lulc - the textual description of the land cover type
            that non-protected areas will transition to
        protection_transition_percent - the amount that a landcover will
            transition towards if not protected
        agriculture_table - a dictionary indexed by
            (old lulc, transition, new lulc type) -> percent improvement
        restoration_table - a dictionary indexed by
            (old lulc, new lulc, transition, activity) -> percent transition
        years_of_transition - a number representing the number of years the
            transition occurs over.  It is not used in the calculation but saved
            for later presentation in the final report.
        returns nothing"""

    #Preprocess the results suffix
    if results_suffix is None:
        results_suffix = ''
    else:
        results_suffix = '_' + results_suffix

    activity_rat = pygeoprocessing.geoprocessing.get_rat_as_dictionary_uri(
        activity_portfolio_dataset_uri)
    activity_desc_to_id = dict(
        [(activity_rat['Activity'][raster_value], raster_value)
         for raster_value in activity_rat['Value']])

    LOGGER.info('loading the directory file registry')
    ipa_directory_file_registry_uri = os.path.join(
        workspace_dir, 'investment_portfolio_adviser_directory_file_registry%s.json' % results_suffix)
    ipa_directory_file_registry_file = open(ipa_directory_file_registry_uri)
    ipa_directory_file_registry = json.load(ipa_directory_file_registry_file)

    LOGGER.debug('saving intermediate state values for RIOS BEER')
    state_values = {
        'years_of_transition': years_of_transition
        }

    porter_dir_registry = {
        'scenario_directory': os.path.join(
            workspace_dir, '2_portfolio_translator_lulc_scenarios')
        }

    porter_file_registry = {
        'base_lulc_uri': os.path.join(
            porter_dir_registry['scenario_directory'],
            'base_lulc%s.tif' % results_suffix),
        'transitioned_lulc_uri': os.path.join(
            porter_dir_registry['scenario_directory'],
            'transitioned_lulc%s.tif' % results_suffix),
        'unprotected_lulc_uri': os.path.join(
            porter_dir_registry['scenario_directory'],
            'unprotected_lulc%s.tif' % results_suffix),
        'base_coefficients_uri': os.path.join(
            porter_dir_registry['scenario_directory'],
            'base_coefficients%s.csv' % results_suffix),
        'transitioned_coefficients_uri': os.path.join(
            porter_dir_registry['scenario_directory'],
            'transitioned_coefficients%s.csv' % results_suffix),
        'unprotected_coefficients_uri': os.path.join(
            porter_dir_registry['scenario_directory'],
            'unprotected_coefficients%s.csv' % results_suffix),
        'directory_file_registry': os.path.join(
            workspace_dir, 'portfolio_translator_directory_file_registry%s.json' %
            results_suffix),
        'porter_state_uri': os.path.join(
            workspace_dir, 'portfolio_translator_state%s.json' % results_suffix)
        }

    with open(porter_file_registry['porter_state_uri'], 'wb') \
            as porter_state_file:
        json.dump(state_values, porter_state_file)

    porter_directory_file_registry_uri = (
        porter_file_registry['directory_file_registry'])
    porter_directory_file_registry_file = open(
        porter_directory_file_registry_uri, 'w')
    json.dump(
        {
            'dir_registry': porter_dir_registry,
            'file_registry': porter_file_registry
        },
        porter_directory_file_registry_file, indent=4)
    porter_directory_file_registry_file.close()

    LOGGER.info('creating PORTER scenarios')
    scenario_directory = porter_dir_registry['scenario_directory']

    if not os.path.exists(scenario_directory):
        os.makedirs(scenario_directory)
    lulc_coefficients_uri = (
        ipa_directory_file_registry['file_registry']
        ['lulc_coefficients_table_uri'])

    lulc_to_coefficents = pygeoprocessing.geoprocessing.get_lookup_from_csv(
        lulc_coefficients_uri, 'lucode')
    lulc_coefficients_reader = csv.reader(open(lulc_coefficients_uri, 'r'))
    lulc_coefficients_headers = lulc_coefficients_reader.next()

    scenario_lulc_list = ['base', 'transitioned', 'unprotected']
    scenario_lulc_dataset = {}
    #create a writer for each output type and dump the CSV headers to them
    for dataset_type in scenario_lulc_list:
        csv_path = porter_file_registry[dataset_type + '_coefficients_uri']
        scenario_lulc_dataset[dataset_type] = \
            {'csv_writer' : csv.writer(open(csv_path, 'wb'))}
        scenario_lulc_dataset[dataset_type]['csv_writer'].\
            writerow(lulc_coefficients_headers)

    header_to_use_converted_value = ['native_veg', 'LULC_veg']

    #Write all the original land properties to the csv file
    #Write all the original column headers to each of the output csvs
    lulc_desc_to_id = {}
    id_to_activity_dict = {}
    for current_lucode in sorted(lulc_to_coefficents.keys()):
        #Take the description of the LULC and map it to the int lucode to be
        #used later
        lulc_desc_to_id[lulc_to_coefficents[current_lucode]['description']] =\
            current_lucode

        id_to_activity_dict[current_lucode] = (
            lulc_to_coefficents[current_lucode]['description'])
        #This maps the output frow from the base general_lulc_coefficents to
        #the columns we need defined in base_output_header_indexes
        output_row = [
            lulc_to_coefficents[current_lucode][header] for header in
            lulc_coefficients_headers]

        #Then write to each of the output datasets
        for dataset in scenario_lulc_dataset.values():
            dataset['csv_writer'].writerow(output_row)

    transition_type_dict = load_transition_types(
        ipa_directory_file_registry['file_registry']['transition_types_uri'])

    #This dictionary will be used to map tuples of the original lucodes and
    #transition codes to the new lucodes.  It'll be used to generate output
    #scenarios
    lucode_transcode_to_new_lucode = {}

    #Write out the new LULC values that will occur from agriculture activities
    #the 3 and 2 come from the different columns in the agriculture and
    #restoration table
    for table, new_lulc_index, is_restoration in [
            (agriculture_table, 3, False), (restoration_table, 3, True)]:
        for new_lulc_tuple, interpolation_value in table.iteritems():
            #original lulc headers
            #new lulc headers
            #Look up the original LULC indexes and the transition index
            original_lulc_desc = new_lulc_tuple[0]
            transition_desc = new_lulc_tuple[1]
            activity_desc = new_lulc_tuple[2]
            new_lulc_desc = new_lulc_tuple[new_lulc_index]

            activity_id = activity_desc_to_id[activity_desc]

            original_lulc_id = lulc_desc_to_id[original_lulc_desc]
            new_lulc_id = lulc_desc_to_id[new_lulc_desc]

            transition_id = (
                transition_type_dict[transition_desc]['raster_value'])

            #These are two lists of the properties we defined as important in
            #rios_to_invest_property_list
            original_properties = lulc_to_coefficents[original_lulc_id]
            new_properties = lulc_to_coefficents[new_lulc_id]

            transitioned_lulc_id = generate_combined_lulc(
                original_lulc_id, transition_id, activity_id, new_lulc_id)

            #Record the transitonied id in the lookup for generating new lulc
            #maps later
            if is_restoration:
                lucode_transcode_to_new_lucode[
                    (original_lulc_id, transition_id, activity_id, new_lulc_id)] = (
                        transitioned_lulc_id)
            else:
                lucode_transcode_to_new_lucode[
                    (original_lulc_id, transition_id, activity_id)] = (
                        transitioned_lulc_id)

            interpolated_values = linear_interpolate(
                original_properties, new_properties, interpolation_value)

            #override some of the interpolated values
            interpolated_values['lucode'] = transitioned_lulc_id
            interpolated_values['description'] = ','.join(new_lulc_tuple[0:4])

            id_to_activity_dict[transitioned_lulc_id] = (
                interpolated_values['description'])

            for header in header_to_use_converted_value:
                interpolated_values[header] = new_properties[header]
            new_values = [
                interpolated_values[x] for x in lulc_coefficients_headers]
            scenario_lulc_dataset['transitioned']['csv_writer'].writerow(
                new_values)
            scenario_lulc_dataset['unprotected']['csv_writer'].writerow(
                new_values)

    LOGGER.debug(lucode_transcode_to_new_lucode)

    #Create the senario lulcs
    #The base lulc only needs to be copied over
    lulc_raster_filename = (
        ipa_directory_file_registry['file_registry']['lulc_uri'])

    base_lulc_uri = porter_file_registry['base_lulc_uri']
    LOGGER.info("Copying %s to %s", lulc_raster_filename, base_lulc_uri)
    shutil.copyfile(lulc_raster_filename, base_lulc_uri)

    #The transitioned lulc needs to be created
    activity_transition_uri = (
        ipa_directory_file_registry['file_registry']
        ['max_transition_activity_portfolio_uri'])
    activity_portfolio_uri = (
        ipa_directory_file_registry['file_registry']
        ['activity_portfolio_uri'])

    max_native_type_uri = (
        os.path.join(os.path.dirname(
            ipa_directory_file_registry['file_registry']
            ['activity_portfolio_uri']), 'max_native_type_id.tif'))

    transition_nodata = pygeoprocessing.geoprocessing.get_nodata_from_uri(
        activity_transition_uri)

    transitioned_lulc_uri = (
        porter_file_registry['transitioned_lulc_uri'])

    base_nodata = pygeoprocessing.geoprocessing.get_nodata_from_uri(
        lulc_raster_filename)
    transitioned_nodata = base_nodata
    def new_lulc_op(original_lulc, transition_id, activity_id, max_native_type):
        """A method for vectorize_rasters that maps lulc and transition values
            to their new land cover types"""
        if original_lulc == base_nodata:
            return transitioned_nodata
        if transition_id == transition_nodata:
            #There's no change, return the original cover
            return original_lulc
        if ((original_lulc, transition_id, activity_id) in
             lucode_transcode_to_new_lucode):
            return lucode_transcode_to_new_lucode[
                (original_lulc, transition_id, activity_id)]
        elif ((original_lulc, transition_id, activity_id, max_native_type) in
             lucode_transcode_to_new_lucode):
            return lucode_transcode_to_new_lucode[
                (original_lulc, transition_id, activity_id, max_native_type)]
        return original_lulc

    cell_size = pygeoprocessing.geoprocessing.get_cell_size_from_uri(
        lulc_raster_filename)

    LOGGER.info('calculating new_lulc_op')
    pygeoprocessing.geoprocessing.vectorize_datasets(
        [lulc_raster_filename, activity_transition_uri, activity_portfolio_uri,
         max_native_type_uri],
        new_lulc_op, transitioned_lulc_uri, gdal.GDT_Int32, transitioned_nodata,
        cell_size, 'intersection', datasets_are_pre_aligned=True)

    #Create the scenario for all protected areas degrading into base types
    avoided_lulc_id = lulc_desc_to_id[avoided_transition_lulc]

    #get a list of protection transition types
    protection_id_list = []
    transition_id_to_desc = {}
    for transition_id, properties in transition_type_dict.iteritems():
        if properties['type'] == 'protection':
            protection_id_list.append(properties['raster_value'])
        transition_id_to_desc[properties['raster_value']] = transition_id

    protected_lulc_ids = set([])

    def protection_conversion_op(original_lulc, transition_id):
        """A method for vectorize_rasters that maps lulc and
            transition values to their new land cover types"""
        if original_lulc == transitioned_nodata:
            return transitioned_nodata
        if transition_id in protection_id_list:
            combined_lulc = original_lulc * 10**3 + transition_id
            protected_lulc_ids.add(
                (original_lulc, transition_id, avoided_lulc_id))

            #There's no change, return the original cover
            return combined_lulc
        return original_lulc

    unprotected_filename = porter_file_registry['unprotected_lulc_uri']
    LOGGER.info('calculating protection_conversion_op')
    pygeoprocessing.geoprocessing.vectorize_datasets(
        [transitioned_lulc_uri, activity_transition_uri],
        protection_conversion_op, unprotected_filename,
        gdal.GDT_Int32, transitioned_nodata, cell_size, 'intersection')

    LOGGER.info('interpolating table headers')
    for original_lulc, transition_id, avoided_lulc in protected_lulc_ids:
        original_properties = lulc_to_coefficents[original_lulc]
        avoided_properties = lulc_to_coefficents[avoided_lulc]

        interpolated_values = linear_interpolate(
            original_properties, avoided_properties,
            float(protection_transition_percent))

        #no need to include the activity in this
        avoided_lulc_id = original_lulc * 10**3 + transition_id

        interpolated_values['lucode'] = avoided_lulc_id
        interpolated_values['description'] = (
            lulc_to_coefficents[original_lulc]['description'] + ',' +
            transition_id_to_desc[transition_id] + ',' +
            lulc_to_coefficents[avoided_lulc]['description'] + ',degraded')

        id_to_activity_dict[avoided_lulc_id] = (
            interpolated_values['description'])

        for header in header_to_use_converted_value:
            interpolated_values[header] = new_properties[header]
        new_values = [
            interpolated_values[x] for x in lulc_coefficients_headers]
        scenario_lulc_dataset['unprotected']['csv_writer'].writerow(new_values)

    LOGGER.debug("id_to_activity_dict %s", id_to_activity_dict)
    #create RAT for base, restored, and degraded
    for raster_uri in [
            base_lulc_uri, transitioned_lulc_uri, unprotected_filename]:
        LOGGER.info(
            "building raster attribute table for %s",
            os.path.basename(raster_uri))
        id_to_description = {}
        nodata = pygeoprocessing.get_nodata_from_uri(raster_uri)
        for lucode in unique_raster_values_uri(raster_uri):
            if lucode != nodata:
                id_to_description[lucode] = id_to_activity_dict[lucode]
        pygeoprocessing.geoprocessing.create_rat_uri(
            raster_uri, id_to_description, "Activity")


def unique_raster_values_uri(raster_uri):
    """Returns a unique list of ids in the integer raster

        raster_uri - a uri path to a gdal raster on disk

        returns - A list of integers that exist in raster_uri
    """
    # Initialize a list that will hold pixel counts for each group
    dataset = gdal.Open(raster_uri, gdal.GA_ReadOnly)
    band = dataset.GetRasterBand(1)

    n_rows = dataset.RasterYSize
    n_cols = dataset.RasterXSize

    block_size = band.GetBlockSize()
    cols_per_block, rows_per_block = block_size[0], block_size[1]
    n_col_blocks = int(math.ceil(n_cols / float(cols_per_block)))
    n_row_blocks = int(math.ceil(n_rows / float(rows_per_block)))

    unique_pixels = numpy.array([], dtype=numpy.int)

    for row_block_index in xrange(n_row_blocks):
        row_offset = row_block_index * rows_per_block
        row_block_width = n_rows - row_offset
        if row_block_width > rows_per_block:
            row_block_width = rows_per_block

        for col_block_index in xrange(n_col_blocks):
            col_offset = col_block_index * cols_per_block
            col_block_width = n_cols - col_offset
            if col_block_width > cols_per_block:
                col_block_width = cols_per_block

            dataset_block = band.ReadAsArray(
                xoff=col_offset, yoff=row_offset, win_xsize=col_block_width,
                win_ysize=row_block_width)

            unique_pixels = numpy.union1d(
                unique_pixels, numpy.unique(dataset_block))

    dataset_block = None
    band = None
    dataset = None

    return unique_pixels


def execute(args):
    """Main entry point for RIOS porter

        args - dictionary of arguments described below

        returns nothing"""

    #Preprocess the results suffix
    LOGGER.debug(args)
    if 'results_suffix' in args:
        results_suffix = args['results_suffix']
        if results_suffix is None:
            results_suffix = ''
        else:
            results_suffix = '_' + results_suffix
    else:
        results_suffix = ''
        args['results_suffix'] = None

    #check for % transitioned in tables
    error_list = []
    for table, label in [
            (args['agriculture_table'], 'Agriculture'),
            (args['restoration_table'], 'Restoration')]:
        for table_row in table.iteritems():
            if not 0 <= table_row[1] <= 1:
                error_list.append(label + ': ' + str(table_row))
    if len(error_list) > 0:
        raise Exception(
            "Value must be between 0 and 1 on the following rows\n" +
            '\n'.join(error_list))

    directory_file_registry_uri = os.path.join(
        args['workspace_dir'], 'investment_portfolio_adviser_directory_' +
        'file_registry%s.json' % results_suffix)
    directory_file_registry_file = open(directory_file_registry_uri)
    directory_file_registry = json.load(directory_file_registry_file)

    activity_portfolio_dataset_uri = (
        directory_file_registry['file_registry']['activity_portfolio_uri'])

    create_scenarios(
        args['workspace_dir'],
        args['results_suffix'],
        args['avoided_transition_lulc'],
        args['protection_transition_percent'],
        args['agriculture_table'],
        args['restoration_table'],
        activity_portfolio_dataset_uri,
        args['years_to_transition'])