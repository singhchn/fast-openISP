# File: image_helpers.py
# Description: Numpy helpers for image processing
# Created: 2021/10/22 20:34
# Author: Qiu Jueqin (qiujueqin@gmail.com)


import numpy as np


def get_bayer_indices(pattern):
    """
    Get (x_start_idx, y_start_idx) for R, Gr, Gb, and B channels
    in Bayer array, respectively
    """

    return {'gbrg': ((0, 1), (1, 1), (0, 0), (1, 0)),
            'rggb': ((0, 0), (1, 0), (0, 1), (1, 1)),
            'bggr': ((1, 1), (0, 1), (1, 0), (0, 0)),
            'grbg': ((1, 0), (0, 0), (1, 1), (0, 1))}[pattern.lower()]


def split_bayer(bayer_array, bayer_pattern):
    """
    Split R, Gr, Gb, and B channels sub-array from a Bayer array
    :param bayer_array: np.ndarray(H, W)
    :param bayer_pattern: 'gbrg' | 'rggb' | 'bggr' | 'grbg'
    :return: 4-element list of R, Gr, Gb, and B channel sub-arrays, each is an np.ndarray(H/2, W/2)
    """

    rggb_indices = get_bayer_indices(bayer_pattern)

    sub_arrays = []
    for idx in rggb_indices:
        x0, y0 = idx
        sub_arrays.append(
            bayer_array[y0::2, x0::2]
        )

    return sub_arrays


def reconstruct_bayer(sub_arrays, bayer_pattern):
    """
    Inverse implementation of split_bayer: reconstruct a Bayer array from a list of
        R, Gr, Gb, and B channel sub-arrays
    :param sub_arrays: 4-element list of R, Gr, Gb, and B channel sub-arrays, each np.ndarray(H/2, W/2)
    :param bayer_pattern: 'gbrg' | 'rggb' | 'bggr' | 'grbg'
    :return: np.ndarray(H, W)
    """

    rggb_indices = get_bayer_indices(bayer_pattern)

    height, width = sub_arrays[0].shape
    bayer_array = np.empty(shape=(2 * height, 2 * width), dtype=sub_arrays[0].dtype)

    for idx, sub_array in zip(rggb_indices, sub_arrays):
        x0, y0 = idx
        bayer_array[y0::2, x0::2] = sub_array

    return bayer_array


def pad(array, pads, mode='reflect'):
    """
    Pad an array with given margins
    :param array: np.ndarray(H, W, ...)
    :param pads: {int, sequence}
        if int, pad top, bottom, left, and right directions with the same margin
        if 2-element sequence: (y-direction pad, x-direction pad)
        if 4-element sequence: (top pad, bottom pad, left pad, right pad)
    :param mode: padding mode, see np.pad
    :return: padded array: np.ndarray(H', W', ...)
    """

    if isinstance(pads, (list, tuple, np.ndarray)):
        if len(pads) == 2:
            pads = ((pads[0], pads[0]), (pads[1], pads[1])) + ((0, 0),) * (array.ndim - 2)
        elif len(pads) == 4:
            pads = ((pads[0], pads[1]), (pads[2], pads[3])) + ((0, 0),) * (array.ndim - 2)
        else:
            raise NotImplementedError

    return np.pad(array, pads, mode)


def shift_array(padded_array, window_size):
    """
    Shift an array within a window and generate window_size**2 shifted arrays
    :param padded_array: np.ndarray(H+2r, W+2r)
    :param window_size: 2r+1
    :return: a generator of length (2r+1)*(2r+1), each is an np.ndarray(H, W), and the original
        array before padding locates in the middle of the generator
    """

    wy, wx = window_size if isinstance(window_size, (list, tuple)) else (window_size, window_size)
    assert wy % 2 == 1 and wx % 2 == 1, 'only odd window size is valid'

    height = padded_array.shape[0] - wy + 1
    width = padded_array.shape[1] - wx + 1

    for y0 in range(wy):
        for x0 in range(wx):
            yield padded_array[y0:y0 + height, x0:x0 + width, ...]


def mean_filter(array, filter_size=3):
    """
    A faster reimplementation of the mean-filter
    :param array: array to be filter: np.ndarray(H, W, ...)
    :param filter_size: int, diameter of the mean-filter
    :return: filtered array: np.ndarray(H, W, ...)
    """

    assert filter_size % 2 == 1, 'only odd filter size is valid'

    padded_array = pad(array, pads=filter_size // 2)
    shifted_arrays = shift_array(padded_array, window_size=filter_size)
    return (sum(shifted_arrays) / filter_size ** 2).astype(array.dtype)


def ycbcr_to_rgb(ycbcr_array):
    """ Convert YCbCr 3-channel array into sRGB array """

    assert ycbcr_array.dtype == np.uint8

    matrix = np.array([[298, 0, 411],
                       [298, -101, -211],
                       [298, 519, 0]], dtype=np.int32).T  # x256
    bias = np.array([-57344, 34739, -71117], dtype=np.int32).reshape(1, 1, 3)  # x256

    ycbcr_array = ycbcr_array.astype(np.int32)
    rgb_array = np.right_shift(ycbcr_array @ matrix + bias, 8)
    rgb_array = np.clip(rgb_array, 0, 255)

    return rgb_array.astype(np.uint8)
