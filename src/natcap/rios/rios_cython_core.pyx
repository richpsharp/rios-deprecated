import numpy

def calculate_priority(float out_nodata, raster_nodata, weights, *pixels):
    """Loop through all values in *pixels and calculate a normalized
        weight value.

        pixels - a python array of numeric values.

        returns a python float between 0.0 and 1.0"""

    cdef float pixel_sum = 0.0
    cdef float user_factor_sum = 0.0

    cdef int index = 0
    cdef float pixel_value_copy = 0.0
    cdef int has_nodata = False

    cdef int riparian_nodata = False
    cdef float onpixel_value = -1.0

    cdef int is_riparian = 0
    cdef int is_onpixel = 0
    cdef float weight = 0.0
    cdef int invert = 0
    cdef float weighted_value = 0.0
    cdef float result = 0.0

    for index in range(len(pixels)):
        pixel_value_copy = numpy.float(pixels[index])
        #weight is a float Invert is a boolean
        weight,invert,is_riparian,is_onpixel = weights[index]

        if pixel_value_copy == raster_nodata[index]:
            if not is_riparian:
                #Nodata value, no need to calculate the rest
                has_nodata = True
                break
            else:
                #don't add the riparian part in, but also don't set the stack
                #to nodata value, we'll bump up on-pixel later
                riparian_nodata = True
                continue

        user_factor_sum += weight

        #Check to see if we need to do the weight*(1-pix) thing
        if invert:
            pixel_value_copy = 1-pixel_value_copy

        weighted_value = weight * pixel_value_copy

        if is_onpixel:
            onpixel_value = pixel_value_copy

        pixel_sum += weight * pixel_value_copy

    if user_factor_sum == 0.0:
        user_factor_sum = 1.0

    #If riparian was nodata and onpixel was defined let
    #onpixel account for the ENTIRE weight of riparian and onpixel
    #super hacky, but at Adrian's request.
    if riparian_nodata and onpixel_value != -1.0:
        #we know on-pixel should be weighted at 0.5, thus hard coded
        #to bump up total to 1.0.  Accounts for missing riparian entry
        pixel_sum += onpixel_value*0.5
        user_factor_sum += 0.5

    result = (pixel_sum / user_factor_sum)

    if has_nodata:
        result = out_nodata

    return result

