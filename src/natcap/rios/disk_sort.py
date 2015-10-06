"""RIOS's disk based pixel sorting routine"""

import tempfile
import struct
import heapq
import atexit
import os

import numpy
import pygeoprocessing


def sort_to_disk(
        dataset_uri, dataset_index, score_weight=1.0,
        cache_element_size=2**17):
    """Sorts the non-nodata pixels in the dataset on disk and returns
    an iterable in sorted order.

    Parameters:
        dataset_uri (string): a path to a floating point GDAL dataset
        score_weight (float): a number to multiply all values by, which can be
            used to reverse the order of the iteration if negative.
        cache_element_size (int): approximate number of single elements to hold
            in memory before flushing to disk.  Due to the internal blocksize
            of the input raster, it is possible this cache could go over
            this value by that size before the cache is flushed.

    Returns:
        an iterable that produces (value * score_weight, flat_index) in
        decreasing sorted order by value * score_weight"""

    def _read_score_index_from_disk(
            score_file_name, index_file_name, buffer_size=1024):
        """Generator to yield a float/int value from the given filenames.
        reads a buffer of `buffer_size` big before to avoid keeping the
        file open between generations."""

        score_buffer = ''
        index_buffer = ''
        file_offset = 0
        buffer_offset = 1  # initialize to 1 to trigger the first load
        while True:
            if buffer_offset >= len(score_buffer):
                score_file = open(score_file_name, 'rb')
                index_file = open(index_file_name, 'rb')
                score_file.seek(file_offset)
                index_file.seek(file_offset)

                score_buffer = score_file.read(buffer_size)
                index_buffer = index_file.read(buffer_size)
                score_file.close()
                index_file.close()

                file_offset += buffer_size
                buffer_offset = 0
            packed_score = score_buffer[buffer_offset:buffer_offset+4]
            packed_index = index_buffer[buffer_offset:buffer_offset+4]
            buffer_offset += 4
            if not packed_score:
                break
            yield (struct.unpack('f', packed_score)[0],
                   struct.unpack('i', packed_index)[0]) + (dataset_index,)

    def _sort_cache_to_iterator(index_cache, score_cache):
        """Flushes the current cache to a heap and returns it

        Parameters:
            index_cache (1d numpy.array): contains flat indexes to the
                score pixels `score_cache`
            score_cache (1d numpy.array): contains score pixels

        Returns:
            Iterable to visit scores/indexes in increasing score order."""

        # sort the whole bunch to disk
        sort_index = score_cache.argsort()
        score_cache = score_cache[sort_index]
        index_cache = index_cache[sort_index]

        #Dump all the scores and indexes to disk
        score_file = tempfile.NamedTemporaryFile(delete=False)
        score_file.write(struct.pack('%sf' % score_cache.size, *score_cache))
        index_file = tempfile.NamedTemporaryFile(delete=False)
        index_file.write(struct.pack('%si' % index_cache.size, *index_cache))

        index_cache = None
        score_cache = None
        sort_index = None

        #Get the filename and register a command to delete it after the
        #interpreter exits
        score_file_name = score_file.name
        score_file.close()
        index_file_name = index_file.name
        index_file.close()

        def _remove_file(path):
            """Function to remove a file and handle exceptions to
                register in atexit."""
            try:
                os.remove(path)
            except OSError:
                # This happens if the file didn't exist, okay because
                # maybe we deleted it in a method
                pass
        atexit.register(_remove_file, score_file_name)
        atexit.register(_remove_file, index_file_name)
        return _read_score_index_from_disk(score_file_name, index_file_name)

    # scale the nodata so they can be filtered out in the sort later
    nodata = pygeoprocessing.get_nodata_from_uri(dataset_uri) * score_weight

    # This will be a list of file iterators we'll pass to heap.merge
    iters = []

    _, n_cols = pygeoprocessing.get_row_col_from_uri(dataset_uri)

    index_cache = numpy.empty((0,), dtype=numpy.int32)
    score_cache = numpy.empty((0,), dtype=numpy.float32)
    for scores_data, scores_block in pygeoprocessing.iterblocks(dataset_uri):
        # flatten and scale the results
        scores_block = scores_block.flatten() * score_weight

        col_coords, row_coords = numpy.meshgrid(
            xrange(scores_data['xoff'], scores_data['xoff'] +
                   scores_data['win_xsize']),
            xrange(scores_data['yoff'], scores_data['yoff'] +
                   scores_data['win_ysize']))

        flat_indexes = (col_coords + row_coords * n_cols).flatten()

        sort_index = scores_block.argsort()
        sorted_scores = scores_block[sort_index]
        sorted_indexes = flat_indexes[sort_index]

        # search for nodata values are so we can splice them out
        left_index = numpy.searchsorted(sorted_scores, nodata, side='left')
        right_index = numpy.searchsorted(
            sorted_scores, nodata, side='right')

        # remove nodata values and sort in decreasing order
        score_cache = numpy.concatenate(
            (score_cache, sorted_scores[0:left_index],
             sorted_scores[right_index::]))
        index_cache = numpy.concatenate(
            (index_cache, sorted_indexes[0:left_index],
             sorted_indexes[right_index::]))

        # check if we need to flush the cache
        if index_cache.size >= cache_element_size:
            iters.append(_sort_cache_to_iterator(index_cache, score_cache))
            index_cache = numpy.empty((0,), dtype=numpy.int32)
            score_cache = numpy.empty((0,), dtype=numpy.float32)

    iters.append(_sort_cache_to_iterator(index_cache, score_cache))
    return heapq.merge(*iters)
