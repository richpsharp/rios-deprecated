"""This module creates an LULC map given an existing LULC map and some
    information about the landcover transitions and activities"""

import logging

from osgeo import gdal
from invest_natcap import raster_utils

LOGGER = logging.getLogger('rios_build_scenarion_lulc')

def execute(args):
    """This function creates an LULC map given an existing LULC map and some
        information about the landcover transitions and activities

        args['output_lulc_uri'] - uri location to the output LULC map
        args['original_lulc_uri'] - the location of the lulc gdal dataset
        args['activity_lookup'] - dictionary to map activity names to raster IDs to activity
          labels and uris'.  Example:
          {
            1: {'label': 'activity_1', 'uri': os.path.join(data_dir, 'activity_1.tif')},
            2: {'label': 'activity_2', 'uri': os.path.join(data_dir, 'activity_2.tif')},
            3: {'label': 'activity_3', 'uri': os.path.join(data_dir, 'activity_3.tif')},
            0: {'label': 'activity_4', 'uri': os.path.join(data_dir, 'activity_4.tif')}
          }

        args['activity_map_filename_uri_list']: filename to the gdal Dataset
            that is the activity portfolio.
        args['transition_uris'] - dictionary to map transition names to
            their uris on disk.
        args['lulc_id_to_description'] - maps lulc ids to their textual
            description
        args['activity_to_transition_function'] - a dictionary that maps how an
            activity maps to a particular transition i.e.:
            { 'activity_1': {'trans_1: 0.2, 'trans_2': 0.4, ...} where
            'trans_1' etc are keys in 'args['transition_uris']
        """

    LOGGER.info('starting rios_build_scenario_lulc')

    lulc_dataset = gdal.Open(args['original_lulc_uri'])

    def op(x):
        return x

    dataset_list = [lulc_dataset]

    raster_utils.vectorize_rasters(dataset_list, op, aoi=None, 
        raster_out_uri=args['output_lulc_uri'], datatype=gdal.GDT_Int32, 
        nodata=0.0)
