"""This file contains core algorithmic functionality of the Water Funds
Prioritizer."""

import logging
import os
import os.path
import math
import json

from osgeo import gdal
import numpy

from invest_natcap.iui import fileio as fileio
import pygeoprocessing
import rios_cython_core

LOGGER = logging.getLogger('rios_core')

def printArgs(args, prefix='', printHeader=True):
    if printHeader:
        LOGGER.info('Printing arguments dictionary')

    for key, value in args.iteritems():
        if isinstance(value, dict):
            print(prefix, unicode(key), 'dict')
            printArgs(value, str(prefix + '------'), False)
        else:
            print(prefix, unicode(key), unicode(value))

    if printHeader:
        LOGGER.info('Finished printing arguments dictionary')

def check_folder(uri):
    """Check to see if the folder at uri exists.  Recursively creates the
        directory structure represented by uri if the path to uri does not
        exist.

        uri - a string uri to a folder on disk.

        returns nothing"""
    if not os.path.exists(uri):
        LOGGER.debug('Creating path %s', uri)
        os.makedirs(uri)

def get_file_uri(basename, extension='tif'):
    """Create a file uri based on the provided basename and extension.  If a
        complete filename is provided for the basename, the complete name is
        returned.  If a complete basename is not provided for the basename,
        .tif is provided as the extension.

        basename - a string basename for a file
        extension='tif' - (optional) a string extension for the basename.

        returns a string filename."""

    name = os.path.splitext(basename)
    if name[1] == '':
        return str(basename + '.' + extension)
    else:
        return basename

def get_output_uri(workspace, filename):
    """Get the output folder uri relative to the input workspace.

        workspace - a string uri to the workspace directory
        filename - the output file name.

        returns a filesystem-appropriate complete path to the output file."""

    base_path = build_uri(workspace, 'output')
    check_folder(base_path)
    return os.path.join(base_path, get_file_uri(filename))

def get_intermediate_uri(workspace, objective, component, filename):
    """Get the intermediate folder uri relative to the input workspace.

        workspace - a string uri to the workspace directory
        objective - (string) the current WARP objective (such as 'Baseflow')
        component - (string) the current component (such as 'sorted')
        filename - the output file name.

        returns a filesystem-appropriate complete path to the intermediate
        file."""

    base_path = build_uri(workspace, 'intermediate', objective, component)
    check_folder(base_path)
    return os.path.join(base_path, get_file_uri(filename))

def build_uri(*args):
    """Build a complete uri out of the provided arguments.  This is abstracted
        to a separate function so that we can change this later on if necessary.

        args - string arguments.

        returns a filesystem-appropriate string filepath."""
    return str(os.path.join(*args))

def dict_transpose(dictionary):
    """Transpose a python dictionary"""
    out_dict = {}
    for outer_key, outer_value in dictionary.iteritems():
        for inner_key, inner_value in outer_value.iteritems():
            if inner_key not in out_dict:
                out_dict[inner_key] = {}
            out_dict[inner_key][outer_key] = inner_value
    return out_dict


def get_value(dictionary, key_list):
    """Recursively search through the input dictionary for the keys in key_list.

        dictionary - a python dictionary
        key_list - a python list of keys

        returns whatever is stored at dictionary[key1][key2]...[keyn]"""

    value = None
    print key_list
    key, remaining_keys = (key_list[0], key_list[1:])
    if key in dictionary:
        if isinstance(dictionary[key], dict):
            value = get_value(dictionary[key], remaining_keys)
        else:
            value = dictionary[key]
    else:
        value = get_value(dictionary, remaining_keys)

    return value


def get_value_bin(value, weight):
    tmp_dict = {}
    tmp_dict['min'] = float(value)
    tmp_dict['max'] = float(value + 1.0)
    tmp_dict['weight'] = weight
    return tmp_dict

def normalize_raster(
    input_raster_uri, output_raster_uri, nodata_output, interp_dict):
    """Map an input raster's values to an output raster based on the provided
        interpolation dictionary.

        input_raster_uri - a uri to a GDAL dataset.
        output_raster_uri - a path to the output GDAL dataset.
        nodata_output: the nodata value for the output raster
        interp_dict: an interpolation dictionary.

        Interpolation dictionary must have the following structure:
            {'type': 'interpolated',
            'interpolation': 'linear',
            'inverted': True | False}
        Other interpolation techniques may be implemented later on.

        returns interpolated GDAL dataset."""

    nodata_input = pygeoprocessing.geoprocessing.get_nodata_from_uri(input_raster_uri)
    interp_type = interp_dict['interpolation']
    if interp_type == 'linear':
        raster_min, raster_max, _, _ = pygeoprocessing.geoprocessing.get_statistics_from_uri(
            input_raster_uri)

        domain = float(raster_max - raster_min)
        #If the domain is 0 that means the numerator of the fraction will
        #always be zero, so just set the denominator to 1.
        if domain == 0:
            domain = 1.0

        if interp_dict['inverted']:
            def interpolate(pixel_array):
                """normalize between 1 and 0 with a -1"""
                invalid_mask = (
                    (pixel_array == nodata_input) | numpy.isnan(pixel_array))
                value = 1.0 - (pixel_array - raster_min) / domain
                return numpy.where(invalid_mask, nodata_output, value)

                #if pixel_value == nodata_input or math.isnan(pixel_value):
                #    return nodata_output
                #return (1.0 - ((pixel_value - raster_min) / domain))
        else:
            def interpolate(pixel_array):
                """normalize between 1 and 0"""
                invalid_mask = (
                    (pixel_array == nodata_input) | numpy.isnan(pixel_array))
                value = (pixel_array - raster_min) / domain
                return numpy.where(invalid_mask, nodata_output, value)


                #if pixel_value == nodata_input or math.isnan(pixel_value):
                #    return nodata_output
                #return (pixel_value - raster_min) / domain

        pixel_size_out = pygeoprocessing.geoprocessing.get_cell_size_from_uri(input_raster_uri)
        pygeoprocessing.geoprocessing.vectorize_datasets(
            [input_raster_uri], interpolate, output_raster_uri,
            gdal.GDT_Float32, nodata_output, pixel_size_out, 'intersection',
            vectorize_op=False)
    else:
        raise Exception("unknown interp_type %s" % interp_type)



def vectorize_raster_sort(input_raster, translate, output_raster):
    """Apply the translate function to input raster to get the output raster.

        input_raster - a GDAL dataset.
        translate - a function that takes a single input variable and never
            returns None.
        output_raster - a GDAL dataset.

        returns nothing."""

    LOGGER.info('Vectorized: sorting values into bins')
    pygeoprocessing.geoprocessing.vectorize_one_arg_op(input_raster.GetRasterBand(1), translate,
        output_raster.GetRasterBand(1))
    LOGGER.info('Vectorized: finished sorting values into bins')


def output_transition_types(transition_list, transition_dictionary, output_uri):
    """Reports the transitions and their types to a file on disk.

    transition_list - a list of dictionaries of at least the entries
        [{
            "file_name": "string"
            "transition_type": "string" (likely protection, restoration, or
            agriculture)
         }, ...]
    transition_dictionary - a dictionary that has at least two keys
        'Max Transition' and 'Value' where the 'Max Transition' key is a
        list of transition names and 'Value' is a list of pixel values on
        a raster.

    output_uri - path and filename to output file"""

    transition_types = {}
    for transition_dict in transition_list:
        transition_type = transition_dict['transition_type']
        transition_name = transition_dict['file_name']
        row = transition_dictionary['Max Transition'].index(transition_name)
        raster_value = transition_dictionary['Value'][row]

        transition_types[transition_dict['file_name']] = {
            'type': transition_type,
            'raster_value': raster_value
            }

    open(output_uri, 'w').write(json.dumps(transition_types, indent = 4))

def output_activity_types(activity_dictionary, output_uri):
    """Reports the activities a json file on disk.

    activity_dictionary - a dictionary of activity names to integer raster codes

    output_uri - path and filename to output file"""

    open(output_uri, 'w').write(json.dumps(activity_dictionary, indent = 4))


def normalize_rasters(args):
    """Open files needed for sorting input rasters into bins.  Calls rios_core
        to execute the actual sorting.

        args['output_dir'] - a string uri to the output directory.
        args['factors'] - a python dictionary of the following form
            {'factor_name':
                {'raster_uri': uri to that raster,
                 'bins': {
                     'interpolation': 'linear',
                     'type': 'interpolated'
                     'inverted': True/False
                     }
                }
             ...}

            returns nothing.
            """
    pygeoprocessing.geoprocessing.create_directories([args['output_dir']])

    for factor_name, factor in args['factors'].iteritems():
        #open input raster, add to args dictionary, this is some hardcoded
        #stuff to handle rasters that need to be generated from converting
        #LULCs into lookup tables.  Those will have a
        #factor['bins']['raster_uri'] defined, but those that don't default
        #to factor['raster_uri']
        try:
            raster_uri = os.path.join(args['output_dir'], factor['bins']['raster_uri'])
        except KeyError:
            raster_uri = factor['raster_uri']

        LOGGER.debug('Opening raster at %s', raster_uri)
        input_dataset = gdal.Open(str(raster_uri))
        factor['input'] = input_dataset

        #for each input raster, create output raster, add to args
        factor_uri = os.path.join(args['output_dir'], factor_name + '.tif')

        #Added this because some of the input nodata values are 0, but
        #generally we're scaling everything between, lets just set to
        #min 32 bit floating point.
        output_nodata = float(numpy.finfo(numpy.float32).min)
        factor['output_uri'] = factor_uri
        factor['output_nodata'] = output_nodata

        if 'type' in factor['bins']:
            LOGGER.info("We're doing normalization because of %s" %
                        factor['bins']['type'])
            normalize_raster(
                raster_uri, factor['output_uri'], factor['output_nodata'],
                factor['bins'])
        elif 'key_field' in factor['bins']:
            #This reclassifies a raster based on a some kind of mapping
            factor['output'] = map_raster_to_table(
                factor['input'], factor['output_uri'], -1.0, factor['bins'])
        else:
            raise Exception("Unknown normalization routine")
