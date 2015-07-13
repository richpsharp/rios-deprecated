""""RIOS IPA execution entry point"""

import webbrowser
import logging
import os
import json
import shutil
import heapq
import datetime

from osgeo import gdal
from osgeo import ogr
from osgeo import osr
import numpy

import natcap.rios.disk_sort
import pygeoprocessing

LOGGER = logging.getLogger('IPA')

def execute(args):
    """wrapper for the _30 entry point"""
    execute_30(**args)


def execute_30(**args):
    """Assemble args dictionaries for the various submodules of WARP and run
        them with these new dictionaries.

        Required contents of args:
            workspace_dir - a string uri for the workspace directory.
            budget_config - a dictionary containing budget configuration
                         information. See rios_portfolio_selection for details
            allocation_config - a dictionary of allocation details.  See
                         rios_portfolio_selection for details.
            activity_potential - a dictionary mapping LULC ids to a list of
                         string activity names.  See rios_portfolio_selection
                         for details.
            lulc_uri - a string URI to a GDAL raster dataset on disk.
            activities - a dictionary mapping protection activities to numeric
                         unit costs.
            objectives - a dictionary of objective dictionaries, where the key
                         of each objective dictionary is the name of the
                         objective.  See below for objective dictionary
                         requirements.
            priorities - a dictionary of activity priority dictionaries.  See
                         the requirements for priority dictionaries in
                         rios_prioritize_activities.
            activity_shapefiles - a python list of URIs to OGR shapefiles.  See
                         rios_portfolio_selection for details of this input.
            general_lulc_coefficients_uri - a URI to the
                general_lulc_coefficients.csv file on disk.
            lulc_activity_potential_map - a dictionary of the form
                {general_lucode0: {'lucode': [user_lulc0, ...], 'activities':
                   ['protection', ...],
                 ...: ...}
            results_suffix - a string suffix to append to each of the output
                files to differentate them between runs.


            objective dictionary:
                A dictionary of values representing attributes for this
                objective.

                contents (required):
                    priorities - a dictionary of activity dictionaries.  See the
                                 rios_prioritize documentation for details on
                                 the requirements for priority dictionaries.
                    factors - a dictionary of factor dictionaries.  See the
                              documentation for rios_sort for details on factor
                              dictionaries.

        returns nothing."""

    if 'results_suffix' in args:
        results_suffix = '_' + args['results_suffix']
    else:
        results_suffix = ''



    LOGGER.info('ensuring that the optional objectives have non-empty factors')
    _update_args_for_optional_parameters(args['objectives'])

    LOGGER.info('Updating references to the general LULC coefficients table')
    _update_args_for_general_lulc_table_refs(
        args['objectives'], args['lulc_coefficients_table_uri'],
        args['lulc_uri'])

    LOGGER.info('Starting Water Funds Prioritizer')

    #make the file registry
    IPA_WORKSPACE = '1_investment_portfolio_adviser_workspace'
    dir_registry = {
        'ipa_workspace': os.path.join(args['workspace_dir'], IPA_WORKSPACE),
        'objective_subdir': 'objectives',
        'objective_transition_subdir': 'objective_level_transitions',
        'normalized_subdir': 'normalized_input_factors',
        'ipa_transition_dir': os.path.join(
            args['workspace_dir'], IPA_WORKSPACE, 'transition_scores'),
        'ipa_activity_dir': os.path.join(
            args['workspace_dir'], IPA_WORKSPACE, 'activity_scores'),
        'ipa_activity_portfolio_dir': os.path.join(
            args['workspace_dir'], IPA_WORKSPACE, 'activity_portfolios'),
        'ipa_report_dir': os.path.join(
            args['workspace_dir'], IPA_WORKSPACE, 'html_report%s' % results_suffix),
        }

    pygeoprocessing.geoprocessing.create_directories([dir_registry['ipa_workspace']])
    file_registry = {
        'lulc_coefficients_table_uri': args['lulc_coefficients_table_uri'],
        'transition_types_uri': os.path.join(
            dir_registry['ipa_workspace'], 'transition_types%s.json' % results_suffix),
        'directory_file_registry': os.path.join(
            args['workspace_dir'], 'investment_portfolio_adviser_directory_file_registry%s.json' % results_suffix),
        'activity_portfolio_uri': os.path.join(
            dir_registry['ipa_activity_portfolio_dir'],
            'activity_portfolio_total%s.tif' % results_suffix),
        'max_transition_activity_portfolio_uri': os.path.join(
            dir_registry['ipa_activity_portfolio_dir'],
            'max_transition_activity_portfolio%s.tif' % results_suffix),
        'ipa_report_uri': os.path.join(
            dir_registry['ipa_report_dir'],
            'ipa_report%s.html' % results_suffix),
        'activity_lookup_table_uri': os.path.join(
            dir_registry['ipa_activity_portfolio_dir'],
            'activity_raster_id_to_type%s.csv' % results_suffix),
        'lulc_uri': args['lulc_uri'],
        }

    #Save the directory and file registry files to a directory
    directory_file_registry_file = open(
        file_registry['directory_file_registry'], 'w')
    json.dump({
            'dir_registry': dir_registry,
            'file_registry': file_registry
            }, directory_file_registry_file, indent=4)
    directory_file_registry_file.close()

    #This is the list of transitions hard coded in the .json object
    transition_list = args['transition_types']

    transition_dictionary = {}
    for transition_index, transition_dict in enumerate(sorted(transition_list)):
        transition_dictionary[transition_dict['file_name']] = {
            'raster_value': transition_index,
            'type': transition_dict['transition_type']
            }

    transition_json_file = open(file_registry['transition_types_uri'], 'w')
    json.dump(transition_dictionary, transition_json_file, indent=4)
    transition_json_file.close()

    if 'objectives' not in args:
        LOGGER.error('No objectives found.  Exiting')
        return

    LOGGER.info('Looping through objectives to sort and prioritize')
    for objective_name, objective_dict in args['objectives'].iteritems():
        #we should only sort and prioritize an objective's biophysical
        #factors if the user has provided biophysical factors.
        LOGGER.debug('OBJECTIVE_DICT %s', objective_dict)
        if objective_dict['rios_model_type'] == 'rios_tier_0':
            LOGGER.debug('Executing a RIOS Tier 0 objective')
            if 'factors' in objective_dict:
                normalize_args = {
                    'output_dir': os.path.join(
                        dir_registry['ipa_workspace'],
                        dir_registry['objective_subdir'],
                        objective_name, dir_registry['normalized_subdir']),
                    'factors': objective_dict['factors'],
                    'results_suffix': results_suffix,
                    'lulc_uri': file_registry['lulc_uri'],
                    }
                _normalize_rasters(normalize_args)

                prioritize_args = {
                    'input_dir': normalize_args['output_dir'],
                    'output_dir': os.path.join(
                        dir_registry['ipa_workspace'],
                        dir_registry['objective_subdir'],
                        objective_name,
                        dir_registry['objective_transition_subdir']),
                    'priorities': objective_dict['priorities'],
                    'results_suffix': results_suffix,
                    'cell_size': \
                        pygeoprocessing.geoprocessing.get_cell_size_from_uri(
                            file_registry['lulc_uri'])
                    }
                _create_objective_transition_scores(prioritize_args)

    LOGGER.info('calculating ipa transition scores')
    transition_args = {
        'input_dir': os.path.join(dir_registry['ipa_workspace'],
                                  dir_registry['objective_subdir']),
        'objective_subdirectory': dir_registry['objective_transition_subdir'],
        'output_dir': dir_registry['ipa_transition_dir'],
        'objective_weights': args['priorities'],
        'results_suffix': results_suffix,
        'cell_size': pygeoprocessing.geoprocessing.get_cell_size_from_uri(
            args['lulc_uri'])
        }
    calculate_global_transitions(transition_args)

    LOGGER.info('Converting transitions to activities')

    activity_score_args = {
        'input_dir': dir_registry['ipa_transition_dir'],
        'output_dir': dir_registry['ipa_activity_dir'],
        'activity_weights': args['transition_map'],
        'results_suffix': results_suffix,
        'transition_dictionary': transition_dictionary,
        'cell_size': pygeoprocessing.geoprocessing.get_cell_size_from_uri(
            args['lulc_uri'])
        }

    calculate_activity_scores(activity_score_args)

    LOGGER.info('Building arguments for budget prioritization')
    budget_args = {
        'budget_config': args['budget_config'],
        'lulc_activity_potential_map': args['lulc_activity_potential_map'],
        'lulc_uri': file_registry['lulc_uri'],
        'activity_shapefiles': args['activity_shapefiles'],
        'results_suffix': results_suffix
        }

    if 'allocation_config' in args:
        budget_args['allocation_config'] = args['allocation_config']

    budget_args['activities'] = {}

    counter = 0
    for activity_name in sorted(args['activities']):
        unit_cost_args = args['activities'][activity_name]
        budget_args['activities'][activity_name] = unit_cost_args
        budget_args['activities'][activity_name]['output_id'] = counter
        budget_args['activities'][activity_name]['prioritization_raster_uri'] =\
            (os.path.join(
                dir_registry['ipa_activity_dir'],
                activity_name + '%s.tif' % results_suffix))
        counter += 1

    #initializing an empty dictionary to hold the output values
    budget_args['output_dir'] = dir_registry['ipa_activity_portfolio_dir']
    budget_args['activity_portfolio_uri'] = (
        file_registry['activity_portfolio_uri'])
    budget_args['max_transition_activity_portfolio_uri'] = (
        file_registry['max_transition_activity_portfolio_uri'])
    budget_args['activity_lookup_table_uri'] = (
        file_registry['activity_lookup_table_uri'])
    budget_args['transition_dictionary'] = dict(
        [(d['raster_value'], d['type']) for d in
         transition_dictionary.values()])

    LOGGER.info('Starting portfolio Selection')
    LOGGER.debug("budget_args %s", str(budget_args))
    report_data = []
    calculate_activity_portfolio(budget_args, report_data)
    LOGGER.info('Finished portfolio selection')

    LOGGER.info('create report')
    generate_report_data = {
        'results_suffix': results_suffix,
        'budget': [],
        'activities': budget_args['activities'],
        }
    for year_index in xrange(args['budget_config']['years_to_spend']):
        year_budget = {
            'year_index': year_index,
            'floating_budget': report_data[year_index]['floating_budget'],
            'activity_budget': report_data[year_index]['activity_budget'],
            'activity_spent': report_data[year_index]['activity_spent'],
            'area_converted': report_data[year_index]['area_converted'],
            }

        generate_report_data['budget'].append(year_budget)


    generate_report_data['ipa_report_uri'] = file_registry['ipa_report_uri']
    _generate_report(dir_registry['ipa_report_dir'], generate_report_data)
    if args['open_html_on_completion']:
        webbrowser.open(file_registry['ipa_report_uri'])

    LOGGER.info('Finished Water Funds Prioritizer')
    LOGGER.info(r'   ____               U  ___ u  ____     ')
    LOGGER.info(r'U |  _"\ u     ___     \/"_ \/ / __"| u  ')
    LOGGER.info(r' \| |_) |/    |_"_|    | | | |<\___ \/   ')
    LOGGER.info(r'  |  _ <       | | .-,_| |_| | u___) |   ')
    LOGGER.info(r'  |_| \_\    U/| |\u\_)-\___/  |____/>>  ')
    LOGGER.info(r'  //   \\_.-,_|___|_,-.  \\     )(  (__) ')
    LOGGER.info(r' (__)  (__)\_)-' '-(_/  (__)   (__)      ')


def _update_args_for_optional_parameters(objectives):
    """This parses out the objectives dictionary and removes factors
        that don't have a URI imput.  We are assuming that if it is
        passed in as such it's allowed."""

    for objective in objectives:
        for factor in objectives[objective]['factors'].keys():
            factor_dict = objectives[objective]['factors'][factor]
            if 'raster_uri' in factor_dict and factor_dict['raster_uri'] == '':
                del objectives[objective]['factors'][factor]
                #loop through the priorities and delete this factor out of it
                for priority in objectives[objective]['priorities']:
                    for priority_objective in objectives[objective]['priorities'][priority].keys():
                        if priority_objective == factor:
                            LOGGER.info("removing objective %s out of priority %s" % (priority_objective, priority))
                            del objectives[objective]['priorities'][priority][priority_objective]

    LOGGER.debug(objectives)

def _update_args_for_general_lulc_table_refs(
        objectives, lulc_coefficients_table_uri, lulc_uri):
    """This parses out the objectives dictionary and replaces any bin table
    URIs with the user-defined general_lulc_coefficient URI.

        objectives - dictionary from the RIOS UI
        lulc_coefficients_table_uri - coefficients table from UI
        lulc_uri - user lulc map from UI

        returns nothing"""
    for objective in objectives:
        for factor in objectives[objective]['factors'].keys():
            try:
                table_uri = (
                    objectives[objective]['factors'][factor]['bins']['uri'])
                general_uri = 'general_lulc_coefficients.csv'
                if table_uri in [os.path.abspath(general_uri), general_uri]:
                    objectives[objective]['factors'][factor]['bins']['uri'] = (
                        lulc_coefficients_table_uri)
                    objectives[objective]['factors'][factor]['bins']['raster_uri'] = lulc_uri
                    LOGGER.debug(
                        'Updating objective/factor uri %s/%s to %s',
                        objective, factor, lulc_coefficients_table_uri)
            except KeyError:
                pass


def calculate_global_transitions(args):
    """This function calculates the weighted average of the objective level
        transitions.

        args['input_dir'] - this is the base directory that contains
            subdirectories of the objectives
        args['objective_subdirectory'] - this is the name of the
            objective_directory/something that contains the objective
            level transitions
        args['output_dir'] - this is the directory to which the global
            transition rasters scores will be saved.
        args['objective_weights'] - this is a dictionary that describes
            the transitions, objectives, and their relative weights of
            the form {'transition_basename1':
                          {'objective_1': weight,
                           ...}
                      ...}
        args['results_suffix'] - a suffix to append to each output filename

        returns nothing"""

    pygeoprocessing.geoprocessing.create_directories([args['output_dir']])

    for transition_basename, objective_weights_dict in args['objective_weights'].iteritems():
        _calculate_global_transition(
            args, transition_basename, objective_weights_dict)


def _calculate_global_transition(args, transition_basename, objective_weights_dict):
    #This gives us a list of basenames and weights in parallel order
    objective_basenames, objective_weights = zip(
        *objective_weights_dict.items())

    #Now map them to explicit URIs so we can call vectorize datasets on them
    objective_uris = [os.path.join(
            args['input_dir'], x, args['objective_subdirectory'],
            transition_basename + '%s.tif' % args['results_suffix']) for x in objective_basenames]

    objective_nodata = [pygeoprocessing.geoprocessing.get_nodata_from_uri(x) for x in objective_uris]
    transition_nodata = -1.0

    #define this function in scope so it uses objective_weights
    def _weighted_transition_average(*pixels):
        """A function for vectorize_datasets to average pixels"""
        weight = numpy.zeros(pixels[0].shape, dtype=numpy.float32)
        nodata_mask = numpy.zeros(pixels[0].shape, dtype=numpy.bool)
        for index, (value, nodata) in enumerate(zip(pixels, objective_nodata)):
            nodata_mask = nodata_mask | (value == nodata)
            weight += value * objective_weights[index]

        #return nodata_mask
        return numpy.where(
            ~nodata_mask, weight / sum(objective_weights), transition_nodata)

    #Boilerplate for vectorize_datasets
    transition_out_uri = os.path.join(
        args['output_dir'],
        transition_basename + '%s.tif' % args['results_suffix'])
    pygeoprocessing.geoprocessing.vectorize_datasets(
        objective_uris, _weighted_transition_average, transition_out_uri,
        gdal.GDT_Float32, transition_nodata, args['cell_size'], "intersection",
        vectorize_op=False)


def calculate_activity_scores(args):
    """Calculates the IPA activity scores by averaging the global transition
        scores that are relevant to each activity

        args['input_dir'] - the directory containing the transition scores
        args['output_dir'] - the directory to hold the activity scores
        args['activity_weights']: a dictionary of transition names to
            dictionary of activity weights, ex: {'transition_name_0': {
             'activity0: 1 or 0,
             ...
             },
         ...}
        args['results_suffix'] - a suffix to append to each output filename
        args['transition_dictionary'] - a mapping of
            { 'transition_name_0': {'raster_value': id, ...}, ...}
            (the transition names are the same as in args['activity_weights'])

        returns nothing"""

    pygeoprocessing.geoprocessing.create_directories([args['output_dir']])

    #Get the basenames but sort them by raster_value in the
    #transition dictionary.  This sorts the items in
    #args['transition_dictonary'] by the raster value, then
    #extracts only the key.  This way we know transition_basenames
    #is in order by raster_value key
    transition_basenames = [x[0] for x in sorted(
        args['transition_dictionary'].items(),
        key=lambda x: x[1]['raster_value'])]

    transition_uris = [
        os.path.join(args['input_dir'], x + '%s.tif' % args['results_suffix'])
        for x in transition_basenames]
    activity_basenames = args['activity_weights'][transition_basenames[0]].keys()

    for activity_basename in activity_basenames:
        _calculate_activity_score(
            activity_basename, transition_basenames, transition_uris, args,
            args['cell_size'])


def _calculate_activity_score(
    activity_basename, transition_basenames, transition_uris, args, cell_size):
    activity_weights = [
        args['activity_weights'][x][activity_basename]
        for x in transition_basenames]

    def _weighted_activity_average(*pixels):
        weight = numpy.zeros(pixels[0].shape)
        for index, value in enumerate(pixels):
            weight += value * activity_weights[index]
        return weight / sum(activity_weights)

    #Boilerplate for vectorize_datasets
    activity_out_uri = os.path.join(
        args['output_dir'], activity_basename + '%s.tif' %
        args['results_suffix'])
    activity_nodata = -1.0
    pygeoprocessing.geoprocessing.vectorize_datasets(
        transition_uris, _weighted_activity_average, activity_out_uri,
        gdal.GDT_Float32, activity_nodata, cell_size, "intersection",
        vectorize_op=False)

    #Make a max transition raster for a particular activity
    transition_activity_out_uri = os.path.join(
        args['output_dir'], 'max_transition_%s%s.tif' %
        (activity_basename, args['results_suffix']))
    transition_nodata = -1
    def _max_transition_activity(*pixels):
        """This calculates the maximum weighted activity
            occuring on a pixel.  If the value is 0.0 we consider it
            nodata."""
        #Weight all the incoming pixels
        weighted_pixels = numpy.array([
            value * activity_weights[index] for index, value in
            enumerate(pixels)])

        #Now find the max indexes
        max_index = numpy.argmax(weighted_pixels, axis=0)
        indices = numpy.indices(max_index.shape)
        max_value = weighted_pixels[max_index, indices[0] ,indices[1]]
        return numpy.where(max_value > 0, max_index, transition_nodata)

    pygeoprocessing.geoprocessing.vectorize_datasets(
        transition_uris, _max_transition_activity, transition_activity_out_uri,
        gdal.GDT_Int32, transition_nodata, cell_size, "intersection",
        vectorize_op=False)


def calculate_activity_portfolio(args, report_data=None):
    """Does the portfolio selection given activity scores, budgets and
        shapefile restrictions.

        args['activities'] - a dictionary describing activity issues like
            {'activity_name0':
               {'out_id': id that goes in a raster,
                'measurement_unit': 'area' or 'linear',
                'unit_cost': unit cost,
                'prioritization_raster_uri': uri to the activity score layer}
             ...}
        args['budget_config'] - dictionary to describe budget selection
            {'years_to_spend': an integer >= 1,
             'activity_budget':
                 {'activity0': {'budget_amount': float >= 0.0},
                  ...}
             'if_left_over': 'Report remainder' or 'Proportionally reallocate',
             'floating_budget': float >= 0.0}
        args['lulc_activity_potential_map'] - a datastructure to map lulc ids
            to which activities are allowed on the map, ex:
            {'general_lucode0':
                {'lucode0': '[list of user's lucodes, '32', ...]',
                 'activities': '[list of allowed activities, 'activity_1', ...]'
                },
             ...},
        args['activity_shapefiles']: [prefer/prevent shapefile uris, ...],
        args['output_dir']: uri for portfolio outputs,
        args['activity_portfolio_uri']: uri for the explicty total activity
            portfolio (this must be known at a global level for intercomponent
            connectivity)
        args['max_transition_activity_portfolio_uri']: uri to the max transition
            raster that causes each activity
        args['lulc_uri']: a link to the original land cover map
        args['results_suffix'] - a suffix to append to each output filename
        args['activity_lookup_table_uri'] - a uri to to dump the activity lookup table
            to.
        args['transition_dictionary'] - a python dictionary that maps transition ids
            to transition names

        report_data - (optional) an input list that when output has the form
           [{
                 year_index: n,
                 floating_budget: n,
                 activity_budget: {
                    'activity_n': n,
                    ...},
                 activity_spent: {
                    'activity_n': n,
                    ...},
                 area_converted: { in Ha
                    'activity_n': n,
                    ...}
            },...
           ]

        returns nothing"""

    #This will keep track of the budget spending
    if report_data == None:
        report_data = []

    pygeoprocessing.geoprocessing.create_directories([args['output_dir']])

    budget_selection_activity_uris = {}

    activity_nodata = -1.0

    #Calculate the amount to offset the activity costs based on 1+ the min per
    #pixel cost.  This will let us uniformly offset all the activity scores in
    #a way that all the prefered activities will come first but still be
    #relatively sorted by priority and ROI.
    min_activity_cost = min([x['unit_cost'] for x in args['activities'].itervalues()])
    prefer_boost = min_activity_cost + 1.0

    #These will be used for heapq.merge iterators later
    activity_iterators = {}
    activity_list = sorted(args['activities'].keys())

    id_to_activity_dict = {}
    for index, activity_name in enumerate(activity_list):
        id_to_activity_dict[index] = activity_name

    _dump_to_table(
        id_to_activity_dict, args['activity_lookup_table_uri'], 'activity_id',
        'activity_type')

    #This will become a list of per activity costs indexed by
    #activity_index
    activity_cost = []

    #THis will be used to record what activity ID in a raster matches
    #to what real world activity.
    activity_raster_lookup = {}

    for activity_name in activity_list:
        args['activities'][activity_name]['prioritization_raster_uri']
        budget_selection_activity_uris[activity_name] = (
            args['activities'][activity_name]['prioritization_raster_uri'] + '_prioritization.tif')

    pixel_size_out = pygeoprocessing.geoprocessing.get_cell_size_from_uri(
        args['lulc_uri'])
    for activity_index, activity_name in enumerate(activity_list):
        activity_dict = args['activities'][activity_name]
        activity_raster_lookup[activity_name] = {
            'index': activity_index,
            'uri': activity_dict['prioritization_raster_uri']
            }

        #Get the normalized cost of activity per unit area, then multiply by
        #the area of a cell to get the per cell cost.  Build as an index for
        #later usage in activity selection
        per_cell_cost = (
            args['activities'][activity_name]['unit_cost'] /
            args['activities'][activity_name]['measurement_value']
            * pixel_size_out ** 2)
        activity_cost.append(per_cell_cost)

        _mask_activity_areas(
            args, activity_dict['prioritization_raster_uri'],
            activity_name, activity_index, activity_nodata,
            budget_selection_activity_uris[activity_name], per_cell_cost,
            prefer_boost, pixel_size_out)


    LOGGER.info('sort the prefer/prevent/activity score to disk')
    for activity_index, activity_name in enumerate(activity_list):
        #Creating the activity iterators here.
        activity_iterators[activity_index] = natcap.rios.disk_sort.sort_to_disk(
            budget_selection_activity_uris[activity_name],
            activity_index)

    #This section counts how many pixels TOTAL we have available for setting
    total_available_pixels = 0
    available_mask_uri = pygeoprocessing.geoprocessing.temporary_filename()
    def _mask_maker(*activity_score):
        """Used to make an activity mask"""
        nodata_mask = numpy.empty(activity_score[0].shape, dtype=numpy.bool)
        nodata_mask[:] = True
        for score in activity_score:
            nodata_mask = nodata_mask & (score == activity_nodata)
        return numpy.where(nodata_mask, activity_nodata, 1)
        #if all(activity_nodata == score for score in activity_score):
        #    return activity_nodata
        #return 1
    pygeoprocessing.geoprocessing.vectorize_datasets(
        budget_selection_activity_uris.values(), _mask_maker,
        available_mask_uri, gdal.GDT_Byte, activity_nodata, pixel_size_out,
        "intersection", dataset_to_align_index=0, vectorize_op=False)
    mask_ds = gdal.Open(available_mask_uri)
    mask_band = mask_ds.GetRasterBand(1)

    n_rows, n_cols = pygeoprocessing.geoprocessing.get_row_col_from_uri(
        available_mask_uri)

    #Make a consistent directory registry.
    directory_registry = {
        'continuous_activity_portfolio': os.path.join(
            args['output_dir'], 'continuous_activity_portfolios'),
        'yearly_activity_portfolio': os.path.join(
            args['output_dir'], 'yearly_activity_portfolios'),
        'total_activity_portfolio': os.path.join(
            args['output_dir'])
        }
    pygeoprocessing.geoprocessing.create_directories(
        directory_registry.values())

    for row_index in range(n_rows):
        mask_array = mask_band.ReadAsArray(0, row_index, n_cols, 1)
        #count the number of pixels not nodata
        total_available_pixels += numpy.sum(mask_array == 1)
    mask_band = None
    mask_ds = None

    activity_array = numpy.memmap(
        pygeoprocessing.geoprocessing.temporary_filename(), dtype=numpy.ubyte,
        mode='w+', shape=(n_rows * n_cols,))
    activity_nodata = 255
    activity_array[:] = activity_nodata

    for year_index in xrange(args['budget_config']['years_to_spend']):
        LOGGER.info('create a portfolio dataset for year %s', year_index + 1)

        #Make a copy of the floating and activity budget.
        try:
            floating_budget = float(args['budget_config']['floating_budget'])
        except ValueError:
            # happens in the offchance that the floating_budget is an empty
            # string.
            floating_budget = 0.

        #The activity budget is indexed in the same order as activity
        #list.. also the same order in which activity_indexes were stored
        #in the heap iterators
        activity_budget = [
            args['budget_config']['activity_budget'][activity_name]
            ['budget_amount'] for activity_name in activity_list]

        #Record the spending
        report_data_dict = {
            'year_index': year_index,
            'floating_budget': floating_budget,
            }
        #This makes a dictionary of activity name to activity budget
        report_data_dict['activity_budget'] = dict([
                (activity_name,
                args['budget_config']['activity_budget'][activity_name]['budget_amount']) for
            activity_name in activity_list])
        #This makes a dictionary of activity name to 0.0, used for spending recording later
        report_data_dict['activity_spent'] = dict([
                (activity_name, 0.0) for activity_name in activity_list])
        report_data_dict['area_converted'] = dict([
                (activity_name, 0.0) for activity_name in activity_list])

        #We'll use this as a data structure to keep track of how many pixels
        #we can spend in each activity
        max_possible_activity_pixels = [
            int(budget/cost) for budget, cost in
            zip(activity_budget, activity_cost)]

        heap_empty = False
        while (sum(max_possible_activity_pixels) > 0 and
               total_available_pixels > 0 and not heap_empty):
            #Assemble the activity iterator by only including those iterators
            #that have budget on the pixel
            valid_activity_iterators = []

            LOGGER.debug("reallocating activity budget pixels")
            for activity_index, pixel_budget in enumerate(
                    max_possible_activity_pixels):
                if pixel_budget > 0:
                    valid_activity_iterators.append(activity_iterators[activity_index])

            if len(valid_activity_iterators) == 0:
                #activity budget left for any pixels, break
                break

            activity_iterator = heapq.merge(*valid_activity_iterators)

            #The heap might be empty, if its not, we'll get inside the
            #for loop and reset it.  This saves us from the tricky case to see if
            #there are any elements left to generate since we can't easily peek
            #ahead on the activity_iterator
            heap_empty = True
            for _, flat_index, activity_index in activity_iterator:
                heap_empty = False

                #See if the pixel has already been allocated
                if activity_array[flat_index] != activity_nodata:
                    continue

                #Otherwise, allocate the pixel
                if total_available_pixels % 10000 == 0:
                    LOGGER.debug("year %s activity: allocating pixel %s for activity %s pixels left %s" % (year_index + 1, flat_index, activity_index,total_available_pixels))
                activity_array[flat_index] = activity_index
                activity_budget[activity_index] -= activity_cost[activity_index]

                #This is complicated index because I set up everything to be
                #indexed by activity index, but in the report we dump according
                #to activity_name
                report_data_dict['activity_spent'][activity_list[activity_index]] += activity_cost[activity_index]
                #the 10,000 is to convert square meters to Ha
                report_data_dict['area_converted'][activity_list[activity_index]] += (pixel_size_out ** 2) / 10000.0

                max_possible_activity_pixels[activity_index] -= 1
                total_available_pixels -= 1
                assert(activity_budget[activity_index] >= 0)
                assert(max_possible_activity_pixels[activity_index] >= 0)

                if max_possible_activity_pixels[activity_index] == 0 or total_available_pixels == 0:
                    #update the iterator
                    break

        LOGGER.debug('finishing activity selection max_possible_activity_pixels %s, total_available_pixels %s heap_empty %s' % (max_possible_activity_pixels, total_available_pixels, heap_empty))

        #Now reallocate any remaining activity budget as float and spend through
        #whatever pixels are left
        if args['budget_config']['if_left_over'] == 'Proportionally reallocate':
            floating_budget += sum(activity_budget)

        #We'll need to keep track of which iterators to use by what kinds of
        #activities we have money left to spend on
        min_cost = min(activity_cost)
        heap_empty = False
        while floating_budget > min_cost and total_available_pixels > 0 and not heap_empty:

            valid_activity_iterators = []
            #we'll use max_cost as a trigger for when the float budget falls below
            #to reallocate the heap iterators
            max_cost = 0.0
            for activity_index, cost in enumerate(activity_cost):
                if cost < floating_budget:
                    valid_activity_iterators.append(
                        activity_iterators[activity_index])
                    max_cost = max(cost, max_cost)

            activity_iterator = heapq.merge(*valid_activity_iterators)

            #It's possible all the heap iterators are empty, this guards against it
            heap_empty = True
            for value, flat_index, activity_index in activity_iterator:
                heap_empty = False

                #See if the pixel has already been allocated
                if activity_array[flat_index] != activity_nodata:
                    continue

                #Otherwise, allocate the pixel
                if total_available_pixels % 10000 == 0:
                    LOGGER.debug("year %s float_budget: allocating pixel %s for activity %s pixels left %s" % (year_index + 1, flat_index, activity_index,total_available_pixels))
                activity_array[flat_index] = activity_index
                floating_budget -= activity_cost[activity_index]
                report_data_dict['activity_spent'][activity_list[activity_index]] += activity_cost[activity_index]
                report_data_dict['area_converted'][activity_list[activity_index]] += (pixel_size_out ** 2) / 10000

                total_available_pixels -= 1
                assert(floating_budget >= 0)

                if max_cost > floating_budget or total_available_pixels == 0:
                    #update the iterator
                    break

        LOGGER.debug('finishing floating floating_budget %s, total_available_pixels %s heap_empty %s' % (floating_budget, total_available_pixels, heap_empty))

        activity_portfolio_uri = os.path.join(
            directory_registry['continuous_activity_portfolio'],
            'activity_portfolio_continuous_year_%s%s.tif' % (year_index + 1, args['results_suffix']))
        _write_array_to_uri(
            activity_array, available_mask_uri, activity_nodata,
            activity_portfolio_uri)
        pygeoprocessing.geoprocessing.calculate_raster_stats_uri(activity_portfolio_uri)
        pygeoprocessing.geoprocessing.create_rat_uri(
            activity_portfolio_uri, id_to_activity_dict, "Activity")

        report_data.append(report_data_dict)

    #Make the stepwise activity budgets
    #Year 1 will just be year 1 continuous
    year_1_activity_dataset_uri = os.path.join(
        directory_registry['yearly_activity_portfolio'],
        'activity_portfolio_year_1%s.tif' % args['results_suffix'])
    shutil.copy(
        os.path.join(
            directory_registry['continuous_activity_portfolio'],
            'activity_portfolio_continuous_year_1%s.tif' % args['results_suffix']),
        year_1_activity_dataset_uri
        )
    pygeoprocessing.geoprocessing.create_rat_uri(
        year_1_activity_dataset_uri, id_to_activity_dict, "Activity")

    #Copy the RAT
    shutil.copy(
        os.path.join(
            directory_registry['continuous_activity_portfolio'],
            'activity_portfolio_continuous_year_1%s.tif.aux.xml' % args['results_suffix']),
        os.path.join(
                directory_registry['yearly_activity_portfolio'],
                'activity_portfolio_year_1%s.tif.aux.xml' % args['results_suffix']))

    #The rest will be the set difference of the current continuous year to the
    #previous
    for year_index in xrange(1, args['budget_config']['years_to_spend']):
        def _subtract_activity_years(prev_year, cur_year):
            return numpy.where(prev_year == cur_year, activity_nodata, cur_year)
            #if prev_year == cur_year:
            #    return activity_nodata
            #return cur_year

        activity_portfolio_uri = [
            os.path.join(
                directory_registry['continuous_activity_portfolio'],
                'activity_portfolio_continuous_year_%s%s.tif' % (year_index, args['results_suffix'])),
            os.path.join(
                directory_registry['continuous_activity_portfolio'],
                'activity_portfolio_continuous_year_%s%s.tif' % (year_index + 1, args['results_suffix']))]

        current_activitiy_portfolio_uri = os.path.join(
            directory_registry['yearly_activity_portfolio'],
            'activity_portfolio_year_%s%s.tif' % (year_index + 1, args['results_suffix']))

        pygeoprocessing.geoprocessing.vectorize_datasets(
            activity_portfolio_uri, _subtract_activity_years,
            current_activitiy_portfolio_uri, gdal.GDT_Byte, activity_nodata,
            pixel_size_out, "intersection", dataset_to_align_index=0,
            vectorize_op=False)
        pygeoprocessing.geoprocessing.create_rat_uri(
            current_activitiy_portfolio_uri, id_to_activity_dict, "Activity")

    #This writes the activity portfolio
    activity_portfolio_uri = args['activity_portfolio_uri']
    _write_array_to_uri(activity_array, available_mask_uri,
                        activity_nodata, activity_portfolio_uri)
    pygeoprocessing.geoprocessing.calculate_raster_stats_uri(activity_portfolio_uri)
    pygeoprocessing.geoprocessing.create_rat_uri(
        activity_portfolio_uri, id_to_activity_dict, "Activity")

    #This writes a raster lookup id
    activity_raster_id_json_uri = os.path.join(
        os.path.dirname(activity_portfolio_uri), 'activity_raster_id.json')
    activity_raster_id_json_file = open(activity_raster_id_json_uri, 'w')
    json.dump(activity_raster_lookup, activity_raster_id_json_file, indent=4)

    #get a list of the activities in order of their index
    #then get a list of the activity uris prepended with "max_transition_"
    #to pass to vectorize datasets
    max_transition_activity_list = []
    for activity_name, activity_dict in sorted(
            activity_raster_lookup.iteritems(), key=lambda x: x[1]['index']):
        activity_dir, activity_filename = os.path.split(activity_dict['uri'])
        max_transition_activity_list.append(
            os.path.join(activity_dir, 'max_transition_' + activity_filename))

    #Create a maximum transition raster based off the activity_portfolio_total
    #raster.
    transition_nodata = -1
    max_activity_transition_raster_uri = (
        args['max_transition_activity_portfolio_uri'])
    def _max_transition_raster(*pixels):
        """pixels[0] is the activity lookup, then pixels[1]...
            is the transition lookup"""
        nodata_mask = pixels[0] == activity_nodata
        value = numpy.empty(pixels[0].shape, dtype=numpy.int32)
        for index in range(1, len(pixels)):
            index_mask = (pixels[0]) == index - 1
            value[index_mask] = pixels[index][index_mask]
        return numpy.where(nodata_mask, transition_nodata, value)

    pygeoprocessing.geoprocessing.vectorize_datasets(
        [activity_portfolio_uri] + max_transition_activity_list,
        _max_transition_raster, max_activity_transition_raster_uri,
        gdal.GDT_Int32, transition_nodata, pixel_size_out, "intersection",
        dataset_to_align_index=0, vectorize_op=False)
    pygeoprocessing.geoprocessing.create_rat_uri(
        max_activity_transition_raster_uri, args['transition_dictionary'],
        "Transition")

def _make_distance_kernel(max_distance):
    kernel_size = int(numpy.round(max_distance * 2 + 1))
    distance_kernel = numpy.empty((kernel_size, kernel_size), dtype=numpy.float)
    for row_index in xrange(kernel_size):
        for col_index in xrange(kernel_size):
            distance_kernel[row_index, col_index] = numpy.sqrt(
                (row_index - max_distance) ** 2 + (col_index - max_distance) ** 2)
    return distance_kernel


def _mask_activity_areas(
    args, prioritization_raster_uri, activity_name, activity_index,
    activity_nodata, budget_selection_activity_uri, per_cell_cost, prefer_boost,
    pixel_size_out):

    prioritization_nodata = pygeoprocessing.geoprocessing.get_nodata_from_uri(
            prioritization_raster_uri)
    mask_uri = {
        'prevent': pygeoprocessing.geoprocessing.temporary_filename(),
        'prefer': pygeoprocessing.geoprocessing.temporary_filename(),
        }

    for activity_type in ['prevent', 'prefer']:
        LOGGER.info('mask out %s shapefile areas for activity %s' % (
                activity_type, activity_name))
        _rasterize_activity_action(
            args['activity_shapefiles'], activity_name, activity_type,
            args['lulc_uri'], mask_uri[activity_type])

    LOGGER.info('mask out lulc prevented areas for each activity')
    lucodes_to_allow = set()
    for lucode, activity_list in args['lulc_activity_potential_map'].iteritems():
        if activity_name in activity_list:
            lucodes_to_allow.add(int(lucode))
    LOGGER.debug('activity_name %s allowed lu codes: %s' % (activity_name, str(lucodes_to_allow)))
    #make sure it's a float for division below
    per_cell_cost = float(per_cell_cost)
    def _activity_prevent_prefer(
            lucode, prevent_mask, prefer_mask, activity_score):
        """masks out the pixels in the activity that are not allowed
            given their landcover type or shapefile mask, bumps
            up pixels that are prefered"""

        #initialize to false
        valid_mask = numpy.zeros(lucode.shape, dtype=numpy.bool)
        for allowed_lucode in lucodes_to_allow:
            valid_mask = valid_mask | (lucode == allowed_lucode)
        valid_mask = valid_mask & (prevent_mask != 1)
        valid_mask = valid_mask & (activity_score != prioritization_nodata)
        return numpy.where(
            valid_mask,
            (activity_score + prefer_mask * prefer_boost) / per_cell_cost,
            activity_nodata)

    pygeoprocessing.geoprocessing.vectorize_datasets(
        [args['lulc_uri'], mask_uri['prevent'], mask_uri['prefer'],
         prioritization_raster_uri], _activity_prevent_prefer,
        budget_selection_activity_uri,
        gdal.GDT_Float32, activity_nodata, pixel_size_out, "intersection",
        dataset_to_align_index=0, vectorize_op=False)


def _write_array_to_uri(array, base_ds_uri, ds_nodata, ds_uri):
    """This is a helper function to write a numpy array to a pre-allocated
        GDAL dataset.

        array - numpy array
        base_ds_uri - a uri to an existsing dataset that will be used to
            define the projection and size of the outgoing dataset
        ds_nodata - the nodata value for the output dataset
        ds_uri - a uri to a valid dataset whose n_rows/n_cols are the same
            dimensions as the array

        returns nothing"""

    pygeoprocessing.geoprocessing.new_raster_from_base_uri(
        base_ds_uri, ds_uri, 'GTiff', ds_nodata,
        gdal.GDT_Byte)
    n_rows, n_cols = pygeoprocessing.geoprocessing.get_row_col_from_uri(ds_uri)
    dataset = gdal.Open(ds_uri, gdal.GA_Update)
    band = dataset.GetRasterBand(1)
    #Need to resize array for writing gdal object
    array.resize((n_rows, n_cols))
    band.WriteArray(array)
    #Reflatten it
    array.resize((n_rows * n_cols,))
    band = None
    dataset = None


def _rasterize_activity_action(shapefile_uri_list, activity_name, action_type, base_uri, out_uri):
    """A helper function that will make a mask of all the features in a list
        of shapefiles that have the requested activty name and action type.

        shapefile_uri_list - a list of shapefile uris which have at least fields
            'activity_n' and 'action'
        activity_name - the name of an activity that might be found in the
            shapefile 'activity_n' field.
        action - the name of an action in the 'action' field of the shapefile
            usually 'prefer' or 'prevent'
        base_uri - a uri to a datasource that will serve as a geotransform and
            cell size reference for the output
        out_uri - the name of the mask output dataset.  it will contain 1 where
            the features in the shapefile_uri_list have the same activity_name
            and action_type and 0 everywhere else.

        returns nothing"""

    #Make the mask raster first, in case we don't do anything else
    pygeoprocessing.geoprocessing.new_raster_from_base_uri(
        base_uri, out_uri, 'GTiff', 0, gdal.GDT_Byte, fill_value=0)

    #Make sure there are some shapefiles in there, if not we're done
    if len(shapefile_uri_list) == 0:
        return

    shapefile_datasets = map(ogr.Open, shapefile_uri_list)
    sample_srs = shapefile_datasets[0].GetLayer(0).GetSpatialRef()

    ogr_driver = ogr.GetDriverByName('Memory')
    temp_shapefile = ogr_driver.CreateDataSource(pygeoprocessing.geoprocessing.temporary_filename())
    temp_layer = temp_shapefile.CreateLayer('temp_shapefile', sample_srs, geom_type=ogr.wkbPolygon)
    temp_layer_defn = temp_layer.GetLayerDefn()

    for shapefile in shapefile_datasets:
        for layer in shapefile:
            for f_index, feature in enumerate(layer):
                shape_activity_name = feature.GetField(
                    feature.GetFieldIndex('activity_n'))
                action = feature.GetField(feature.GetFieldIndex('action'))

                # This is where we get to use the column we created above, to
                # determine if the current feature represents an area where the
                # activity is prevented and set the value of the field
                # accordingly.
                if shape_activity_name == activity_name and action == action_type:
                    LOGGER.debug('Creating feature %s in temp layer', f_index)
                    feat_geometry = feature.GetGeometryRef()
                    temp_feature = ogr.Feature(temp_layer_defn)
                    temp_layer.CreateFeature(temp_feature)
                    temp_feature.SetGeometry(feat_geometry)
                    temp_feature.SetFrom(feature)
                    temp_layer.SetFeature(temp_feature)
                    temp_feature.Destroy()
                else:
                    # Make a note of which activity/action/feature combination
                    # we're skipping, just for information.
                    LOGGER.debug('SKIPPING: %s , %s  && %s, %s',
                        activity_name, shape_activity_name, action,
                        action_type)
            # We need to reset the reading here ... this resets the looping
            # counter so that the next time we loop over this shapefile, we'll
            # start at the first feature.
            layer.ResetReading()

    # Just in case anything has not been flushed to disk, do so now.
    temp_layer.SyncToDisk()

    # Rasterize this layer onto the copied raster.
    mask_dataset = gdal.Open(out_uri, gdal.GA_Update)
    gdal.RasterizeLayer(mask_dataset, [1], temp_layer, burn_values=[1])


def _normalize_raster(
        input_raster_uri, lulc_uri, output_raster_uri, nodata_output, interp_dict,
        pixel_size_out):
    """Map an input raster's values to an output raster based on the provided
        interpolation dictionary.

        input_raster_uri - a uri to a GDAL dataset.
        lulc_uri - a uri to the landcover map to align and clip the result
        output_raster_uri - a path to the output GDAL dataset.
        nodata_output: the nodata value for the output raster
        interp_dict: an interpolation dictionary.

        Interpolation dictionary must have the following structure:
            {'type': 'interpolated',
            'interpolation': 'linear',
            'inverted': True | False}
        Other interpolation techniques may be implemented later on.

        returns interpolated GDAL dataset."""

    LOGGER.debug('_normalize_raster')
    nodata_input = pygeoprocessing.geoprocessing.get_nodata_from_uri(input_raster_uri)
    interp_type = interp_dict['interpolation']
    if interp_type == 'linear':
        raster_min, raster_max, _, _ = pygeoprocessing.geoprocessing.get_statistics_from_uri(
            input_raster_uri)
        LOGGER.debug('raster_min, raster_max %f %f' % (raster_min, raster_max))
        domain = float(raster_max - raster_min)
        #If the domain is 0 that means the numerator of the fraction will
        #always be zero, so just set the denominator to 1.
        if domain == 0:
            domain = 1.0

        if interp_dict['inverted']:
            def interpolate(pixel_value, lulc_value_garbage):
                invalid_mask = (pixel_value == nodata_input) | numpy.isnan(pixel_value)
                value = (1.0 - ((pixel_value - raster_min) / domain))
                return numpy.where(invalid_mask, nodata_output, value)
                #if pixel_value == nodata_input or math.isnan(pixel_value):
                #    return nodata_output
                #return (1.0 - ((pixel_value - raster_min) / domain))
        else:
            def interpolate(pixel_value, lulc_value_garbage):
                invalid_mask = (pixel_value == nodata_input) | numpy.isnan(pixel_value)
                value = (pixel_value - raster_min) / domain
                return numpy.where(invalid_mask, nodata_output, value)
                #if pixel_value == nodata_input or math.isnan(pixel_value):
                #    return nodata_output
                #return (pixel_value - raster_min) / domain

        LOGGER.debug('_normalize_raster calling vectorize datasets')
        pygeoprocessing.geoprocessing.vectorize_datasets(
            [input_raster_uri, lulc_uri], interpolate, output_raster_uri,
            gdal.GDT_Float32, nodata_output, pixel_size_out, 'intersection',
            dataset_to_align_index=1, vectorize_op=False)
    else:
        raise Exception("unknown interp_type %s" % interp_type)


def _normalize_rasters(args):
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
         args['lulc_uri'] - path to the IPA general LULC raster
            for mapping.
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
            raster_uri = os.path.join(
                args['output_dir'], factor['bins']['raster_uri'])
            #This is a hack patch from how we used to hard record
            #the general lulc in the UI, but now have a flexible
            #directory registry.  With 3 days left, not a priority
            #to rewrite this part, so sorry future engineer.
            LOGGER.debug('it was defined, must need a LULC')
            raster_uri = args['lulc_uri']
        except KeyError:
            raster_uri = factor['raster_uri']

        factor['input_uri'] = str(raster_uri)
        #for each input raster, create output raster, add to args
        factor_uri = os.path.join(
            args['output_dir'], factor_name + '%s.tif' % args['results_suffix'])

        #This is a magic standard nodata value
        output_nodata = -9999
        factor['output_uri'] = factor_uri
        factor['output_nodata'] = output_nodata

        if 'type' in factor['bins']:
            LOGGER.info(
                "We're doing normalization because of %s",
                factor['bins']['type'])
            _normalize_raster(
                raster_uri, args['lulc_uri'], factor['output_uri'],
                factor['output_nodata'], factor['bins'],
                pygeoprocessing.geoprocessing.get_cell_size_from_uri(
                    args['lulc_uri']))

        elif 'key_field' in factor['bins']:
            _map_raster_to_table(
                factor['input_uri'], factor['output_uri'], -1.0, factor['bins'])
        else:
            raise Exception("Unknown normalization routine")



def _create_objective_transition_scores(args):
    """Creates transition scores for each transition on a particular
        objective..

        args['input_dir'] - a string uri to the workspace directory that
            contains the normalized rasters.
        args['output_dir'] - a string uri to a directory to store the
            the prioritized transition rasters
            contains the normalized rasters.

        args['objective_name'] - a string name for the objective
        args['priorities'] - a dictionary of the form
            {'transition type: {'Objective Weight' weight, ...},
             ...: ..., ...}

        returns nothing"""

    pygeoprocessing.geoprocessing.create_directories([args['output_dir']])

    for transition_name, factors in args['priorities'].iteritems():
        transition_uri = os.path.join(args['output_dir'], transition_name + '%s.tif' % args['results_suffix'])
        LOGGER.info('Creating %s transition raster', transition_uri)

        raster_list = []
        weights = []
        raster_nodata = []

        for factor_name, factor_weight in factors.iteritems():
            raster_list.append(os.path.join(args['input_dir'], factor_name + '%s.tif' % args['results_suffix']))
            raster_nodata.append(pygeoprocessing.geoprocessing.get_nodata_from_uri(raster_list[-1]))
            try:
                weights.append(
                    (float(factor_weight), False,
                     factor_name=='Riparian continuity',
                     factor_name=='On-pixel retention'))
            except ValueError:
                #The factor_weight must have a ~ in front
                weights.append(
                    (float(str(factor_weight)[1:]), True,
                     factor_name=='Riparian continuity',
                     factor_name=='On-pixel retention'))

        _create_objective_transition_score(
            raster_nodata, weights, raster_list, transition_uri,
            args['cell_size'])


def _create_objective_transition_score(
    raster_nodata, weights, raster_list, transition_uri, cell_size):
    """creates objective transition socres"""

    out_nodata = -1.0
    def calculate_priority(*pixels):
        """Loop through all values in *pixels and calculate a normalized
            weight value.

            pixels - a python array of numeric values.

            returns a python float between 0.0 and 1.0"""
        pixel_sum = numpy.zeros(pixels[0].shape)
        user_factor_sum = numpy.zeros(pixels[0].shape)

        onpixel_value = numpy.empty(pixels[0].shape)
        onpixel_value[:] = -1.0

        nodata_mask = numpy.zeros(pixels[0].shape, dtype=numpy.bool)
        riparian_nodata_mask = numpy.zeros(pixels[0].shape, dtype=numpy.bool)

        for index in range(len(pixels)):
            pixel_value_copy = pixels[index].copy()
            #weight is a float Invert is a boolean
            weight, invert, is_riparian, is_onpixel = weights[index]

            raster_nodata_mask = (pixel_value_copy == raster_nodata[index])

            if is_riparian:
                riparian_nodata_mask = raster_nodata_mask
            else:
                nodata_mask = raster_nodata_mask | nodata_mask

            user_factor_sum += numpy.where(raster_nodata_mask, 0, weight)

            #Check to see if we need to do the weight*(1-pix) thing
            if invert:
                pixel_value_copy = numpy.where(
                    raster_nodata_mask, raster_nodata[index],
                    1-pixel_value_copy)

            #we should only ever have one on-pixel value
            if is_onpixel:
                onpixel_value = numpy.where(
                    raster_nodata_mask, -1.0, pixel_value_copy)

            pixel_sum += numpy.where(
                raster_nodata_mask, 0, weight * pixel_value_copy)

        user_factor_sum = numpy.where(
            user_factor_sum == 0.0, 1.0, user_factor_sum)

        #If riparian was nodata and onpixel was defined let
        #onpixel account for the ENTIRE weight of riparian and onpixel
        #super hacky, but at Adrian's request.
        pixel_sum += numpy.where(
            ~nodata_mask & riparian_nodata_mask & (onpixel_value != -1.0),
            onpixel_value*0.5, 0)
        user_factor_sum += numpy.where(
            ~nodata_mask & riparian_nodata_mask & (onpixel_value != -1.0), 0.5,
            0)

        result = (pixel_sum / user_factor_sum)
        return numpy.where(nodata_mask, out_nodata, result)

    pygeoprocessing.geoprocessing.vectorize_datasets(
        raster_list, calculate_priority, transition_uri, gdal.GDT_Float32,
        out_nodata, cell_size, "intersection", vectorize_op=False)


def _map_raster_to_table(
        input_raster_uri, output_raster_uri, out_nodata, bins):
    """Reclassify the values from input raster into bins and save to
       output_raster_uri.

        input_raster_uri - a GDAL raster dataset.
        output_raster_uri - the path to the GDAL raster dataset.
        out_nodata - The nodata value for the output dataset
        bins - a dictionary of dictionaries.  See rios_sort.execute() for the
               required structure.

        returns the mapped raster."""

    input_to_output_map = {}
    mapped_values = pygeoprocessing.geoprocessing.get_lookup_from_table(
        bins['uri'], 'lucode')

    for lucode, properties in mapped_values.iteritems():
        input_to_output_map[lucode] = properties[bins['value_field'].lower()]

    LOGGER.debug(input_to_output_map)

    output_raster_datatype = gdal.GDT_Float32
    #add a nodata value
    raster_nodata = pygeoprocessing.get_nodata_from_uri(bins['raster_uri'])
    input_to_output_map[raster_nodata] = out_nodata

    #This fixes an issue where the table might have blank inputs and create
    #string based keys and values.
    for key in input_to_output_map.keys():
        try:
            _ = int(key)
        except ValueError:
            del input_to_output_map[key]
    pygeoprocessing.geoprocessing.reclassify_dataset_uri(
        bins['raster_uri'], input_to_output_map, raster_out_uri=output_raster_uri,
        out_datatype = output_raster_datatype, out_nodata=out_nodata,
        exception_flag='values_required')

    LOGGER.debug('Finished normalizing into dictionary bins')


def _generate_report(report_dir, report_data):
    """This function will generate an HTML report about the IPA run including
        information about budget spending and locations of file.

        report_dir - the directory to hold the HTML report.  Assume this directory
            exists
        report_data - a dictionary of the form
        report_data['ipa_report_uri'] - a uri to the .html report file
        report_data['results_suffix'] - (optional) a string describing the run
        report_data['budget'] - a list of dictionaries of the form:
            {
                n: {  # the year index
                     floating_budget: n,
                     activity_budget: {
                        'activity_n': n,
                        ...},
                     activity_spent: {
                        'activity_n': n,
                        ...}
                     area_converted: {
                        'activity_n': n,
                        ...},
                }
            }
         report_data['files'] - a dictionary of file uris
             {'file1': uri,
             }

        returns nothing"""

    time_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    pygeoprocessing.geoprocessing.create_directories([report_dir])

    report_page_uri = report_data['ipa_report_uri']
    report_file = open(report_page_uri, 'w')
    current_dir = os.path.dirname(os.path.abspath(__file__))
    shutil.copyfile(
        os.path.join(current_dir, 'report_style.css'),
        os.path.join(report_dir, 'report_style.css'))

    if 'results_suffix' in report_data:
        results_suffix = '(%s)' % report_data['results_suffix']
    else:
        results_suffix = ''

    #The float budget is the sum of all the yearly ones
    total_float_budget = 0.0
    for year_index in xrange(len(report_data['budget'])):
        total_float_budget += report_data['budget'][year_index]['floating_budget']

    total_budget = total_float_budget
    total_spent = 0.0

    report_file.write('<html><head>')
    report_file.write('<link rel="stylesheet" href="report_style.css">')
    report_file.write('</head><body><div class="content">')

    if len(results_suffix) > 2:
        report_file.write('<h1>Investment Portfolio Adviser Report for run %s</h1>' % (results_suffix))
    else:
        report_file.write('<h1>Investment Portfolio Adviser Report</h1>')

    report_file.write('<p><em>Run on %s</em></p>' % (time_date))

    report_file.write(
        '<ul><li><a href="#ipa_total">RIOS Investment Portfolio Adviser Total Summary</a></li>'
        '<li><a href="#ipa_annual_section">RIOS Investment Portfolio Adviser Annual Budget Reports</a></li>'
        '<ul>')
    for year_index in xrange(len(report_data['budget'])):
        report_file.write(
            '<li><a href="#ipa_year_%s">Year %s Summary</a></li>' % (year_index+1, year_index+1,))
    report_file.write('</ul></ul>')

    report_file.write('<div id="ipa_total" class="report_section">')
    report_file.write('<h2>Total Budget Report</h2><div class=budget_year>')
    report_file.write('<div class="budget_year_title"><h3>All Years</h3></div>')
    report_file.write('<table><thead><tr><th>Activity Type (raster id)</th><th>Actual Spent</th><th>Total Budgeted</th><th>Area Converted (Ha)</th></tr></thead>')
    report_file.write('<tr class="floating_budget"><th>Floating Budget</th><td>%s</td><td>%s</td><td>%s</td></tr>' % ('n/a', total_float_budget, 'n/a'))
    total_area = 0.0
    for activity_name in sorted(report_data['budget'][0]['activity_budget']):
        total_activity_budget = sum([report_data['budget'][year_index]['activity_budget'][activity_name] for
                               year_index in xrange(len(report_data['budget']))])
        total_activity_spent = sum([report_data['budget'][year_index]['activity_spent'][activity_name] for
                               year_index in xrange(len(report_data['budget']))])
        total_activity_area = sum([report_data['budget'][year_index]['area_converted'][activity_name] for
                               year_index in xrange(len(report_data['budget']))])
        activity_id = report_data['activities'][activity_name]['output_id']

        total_budget += total_activity_budget
        total_spent += total_activity_spent
        total_area += total_activity_area

        row_class = 'activity'
        report_file.write('<tr class="%s"><th>%s (%s)</th><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                row_class, activity_name, activity_id, total_activity_spent, total_activity_budget, total_activity_area))

    report_file.write('<tr class="budget_totals"><th>Total</th><td>%s</td><td>%s</td><td>%s</td></tr>' % (total_spent, total_budget, total_area))
    report_file.write('</table></div></div>')

    LOGGER.debug(report_data['budget'])

    report_file.write('<div id="ipa_annual_section" class="report_section">')
    report_file.write('<h2 id=ipa_annual_section>Annual Budget Reports</h2>')
    for year_index in xrange(len(report_data['budget'])):
        float_budget = report_data['budget'][year_index]['floating_budget']
        total_budget = float_budget
        total_spent = 0.0
        total_area = 0.0

        report_file.write('<div id="ipa_year_%s" class=budget_year>' % (year_index+1,))
        report_file.write('<div class="budget_year_title"><h3>Year %s</h3></div>' % (year_index + 1))
        report_file.write('<table><thead><tr><th>Activity Type (raster id)</th><th>Actual Spent</th><th>Total Budgeted</th><th>Area Converted (Ha)</th></tr></thead>')
        report_file.write('<tr><th>Floating Budget</th><td>%s</td><td>%s</td><td>%s</td></tr>' % ('n/a', float_budget, 'n/a'))

        for activity_name in sorted(report_data['budget'][year_index]['activity_budget']):
            activity_budget = report_data['budget'][year_index]['activity_budget'][activity_name]
            activity_spent = report_data['budget'][year_index]['activity_spent'][activity_name]
            activity_area = report_data['budget'][year_index]['area_converted'][activity_name]

            activity_id = report_data['activities'][activity_name]['output_id']

            total_budget += activity_budget
            total_spent += activity_spent
            total_area += activity_area

            report_file.write('<tr><th>%s (%s)</th><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                    activity_name, activity_id, activity_spent, activity_budget, activity_area))

        report_file.write('<tr class="budget_totals"><th>Total</th><td>%s</td><td>%s</td><td>%s</td></tr>' % (total_spent, total_budget, total_area))
        report_file.write('</table>')
        report_file.write('</div>')  # ends budget_year div
    report_file.write('</div>')
    report_file.write('<p class=right_data><em>RIOS version %s</em><br/>' % natcap.rios.__version__)
    report_file.write('</div>')  # ends the content div

    report_file.write('</body></html>')


def _dump_to_table(dictionary, table_uri, key_name, value_name):
    """A function to take a flat dictionary and dump to a CSV
        table.

        dictionary - a flat python dictionary of key/value pairs
        table_uri - the URI of a CSV output table
        key_name - a string to use for the key headings
        value_name - a string to use for the value headings

        returns nothing"""

    with open(table_uri, 'wb') as table_file:
        table_file.write('%s, %s\n' % (key_name, value_name))
        for key, value in dictionary.iteritems():
            table_file.write('%s, %s\n' % (key, value))


def make_exponential_decay_kernel_uri(expected_distance, kernel_uri):
    max_distance = expected_distance * 5
    kernel_size = int(numpy.round(max_distance * 2 + 1))

    driver = gdal.GetDriverByName('GTiff')
    kernel_dataset = driver.Create(
        kernel_uri.encode('utf-8'), kernel_size, kernel_size, 1, gdal.GDT_Float32,
        options=['BIGTIFF=IF_SAFER'])

    #Make some kind of geotransform, it doesn't matter what but
    #will make GIS libraries behave better if it's all defined
    kernel_dataset.SetGeoTransform( [ 444720, 30, 0, 3751320, 0, -30 ] )
    srs = osr.SpatialReference()
    srs.SetUTM( 11, 1 )
    srs.SetWellKnownGeogCS( 'NAD27' )
    kernel_dataset.SetProjection( srs.ExportToWkt() )

    kernel_band = kernel_dataset.GetRasterBand(1)
    kernel_band.SetNoDataValue(-9999)

    col_index = numpy.array(xrange(kernel_size))
    integration = 0.0
    for row_index in xrange(kernel_size):
        distance_kernel_row = numpy.sqrt(
            (row_index - max_distance) ** 2 + (col_index - max_distance) ** 2).reshape(1,kernel_size)
        kernel = numpy.where(
            distance_kernel_row > max_distance, 0.0, numpy.exp(-distance_kernel_row / expected_distance))
        integration += numpy.sum(kernel)
        kernel_band.WriteArray(kernel, xoff=0, yoff=row_index)

    for row_index in xrange(kernel_size):
        kernel_row = kernel_band.ReadAsArray(
            xoff=0, yoff=row_index, win_xsize=kernel_size, win_ysize=1)
        kernel_row /= integration
        kernel_band.WriteArray(kernel_row, 0, row_index)
