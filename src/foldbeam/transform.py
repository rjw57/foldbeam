"""
Geographic co-ordinate transformation
=====================================

This module contains support functions for transforming between different geographic co-ordinate systems.

"""

from . import core
import numpy as np
import os
from osgeo import gdal
import pyproj

def compute_warp(dst_envelope, dst_size, src_spatial_reference):
    """Compute the projection co-ordinates in a source spatial projection for pixels in a destination image.

    :param dst_envelope: the envelope of the destination raster
    :type dst_envelope: :py:class:`core.Envelope`
    :param dst_size: the width and height of the destination raster
    :type dst_size: pair of integer
    :param src_spatial_reference: co-ordinate system of the source raster
    :type src_spatial_reference: :py:class:`osgeo.osr.SpatialReference`
    :rtype: pair of arrays

    Compute the projection co-ordinates of each pixel in a destination raster when projected into the source spatial
    reference. This is necessary to re-project images correctly.

    The return value is a pair of array-like objects giving the x and y co-ordinates. The returned arrays are the width
    and height specified in dst_size.

    """

    # Compute x- and y-co-ordinates in dst from the envelope
    dst_cols, dst_rows = dst_size
    dst_x = np.repeat(
            np.linspace(dst_envelope.left, dst_envelope.right, dst_cols).reshape(1, dst_cols),
            dst_rows, 0)
    dst_y = np.repeat(
            np.linspace(dst_envelope.top, dst_envelope.bottom, dst_rows).reshape(dst_rows, 1),
            dst_cols, 1)

    assert dst_x.shape == (dst_rows, dst_cols)
    assert dst_y.shape == (dst_rows, dst_cols)

    # Special case when source and destination have same srs
    if dst_envelope.spatial_reference.IsSame(src_spatial_reference):
        return dst_x, dst_y

    dst_proj = pyproj.Proj(dst_envelope.spatial_reference.ExportToProj4())
    src_proj = pyproj.Proj(src_spatial_reference.ExportToProj4())

    src_x, src_y = pyproj.transform(dst_proj, src_proj, dst_x, dst_y)

    return src_x, src_y

def proj_to_pixels(x, y, envelope, size):
    """Compute pixel co-ordinates of projection co-ordinates x and y in image with envelope and size specified."""

    off = envelope.offset()
    x = (x - envelope.left) * (float(size[0]-1) / off[0])
    y = (y - envelope.top) * (float(size[1]-1) / off[1])
    return x,y

def pixels_to_proj(x, y, envelope, size):
    """Compute projection co-ordinates of pixel co-ordinates x and y in image with envelope and size specified."""

    off = envelope.offset()
    x = x * (off[0] / float(size[0]-1)) + envelope.left
    y = y * (off[1] / float(size[1]-1)) + envelope.right
    return x,y

def sample_raster(src_pixel_x, src_pixel_y, src_raster):
    """Sample pixels from a raster.

    :param src_pixel_x: array of pixel x-co-ordinates
    :param src_pixel_y: array of pixel y-co-ordinates
    :param src_raster: source raster
    :type src_raster: :py:class:`core.Raster`
    :rtype: :py:class:`numpy.array` or :py:class:`numpy.ma.array`

    The returned array has the same shape as src_raster with each value corresponding to the sampled value. The arrays
    src_pixel_x and src_pixel_y must have the same width and height as src_raster. If pixel co-ordinates outside of the
    range of those present in src_raster are specified, the values will be masked out of the resulting array and a numpy
    masked array will be returned.

    """

    px = np.int32(np.round(src_pixel_x))
    py = np.int32(np.round(src_pixel_y))

    x_valid = np.logical_and(px >= 0, px < src_raster.array.shape[1])
    y_valid = np.logical_and(py >= 0, py < src_raster.array.shape[0])
    valid = np.logical_and(x_valid, y_valid)

    valid_flag = valid.ravel()
    valid_src_indices = np.ravel_multi_index(
        (py.ravel()[valid_flag], px.ravel()[valid_flag]),
        src_raster.array.shape[:2]
    )

    dst_shape = np.atleast_2d(src_pixel_x).shape[:2] + (src_raster.array.shape[2],)
    dst = np.empty(shape=dst_shape, dtype=np.float32)

    for i in xrange(dst_shape[2]):
        dst[valid, i] = src_raster.array[:,:,i].ravel()[valid_src_indices]

    dst = np.ma.fix_invalid(
        dst,
        fill_value=np.nan,
        mask=np.repeat(np.atleast_3d(np.logical_not(valid)), dst_shape[2], 2)
    )

    return dst

def reproject_raster(dst, src):
    """Re-project a source raster into a destination raster.

    See :py:func:`reproject_rasters`.

    """
    reproject_rasters(dst, (src,))

def _py_reproject_rasters(dst, srcs):
    if len(srcs) == 0:
        return

    src_srs = srcs[0].envelope.spatial_reference
    assert all([x.envelope.spatial_reference.IsSame(src_srs) for x in srcs[1:]])

    dst_height, dst_width = dst.array.shape[:2]
    src_x, src_y = compute_warp(dst.envelope, (dst_width, dst_height), src_srs)
    for src in srcs:
        src_height, src_width = src.array.shape[:2]

        # Compute warp
        src_px, src_py = proj_to_pixels(src_x, src_y, src.envelope, (src_width, src_height))
        sample = sample_raster(src_px, src_py, src)

        bands = min(sample.shape[2], dst.array.shape[2])
        dst.array[:,:,:bands] = np.ma.filled(sample[:,:,:bands], dst.array[:,:,:bands])

def _gdal_reproject_rasters(dst, srcs):
    if len(srcs) == 0:
        return

    src_srs = srcs[0].envelope.spatial_reference
    assert all([x.envelope.spatial_reference.IsSame(src_srs) for x in srcs[1:]])

    mem_driver = gdal.GetDriverByName('MEM')
    dst_ds = mem_driver.CreateCopy('', dst.as_dataset())
    src_wkt = src_srs.ExportToWkt()
    dst_wkt = dst.envelope.spatial_reference.ExportToWkt()
    for src in srcs:
        gdal.ReprojectImage(
            src.as_dataset(), dst_ds,
            src_wkt, dst_wkt,
            gdal.GRA_Bilinear if src.can_interpolate else gdal.GRA_NearestNeighbour)

    dst.array = core.Raster.from_dataset(dst_ds).array

reproject_rasters = _py_reproject_rasters
if 'FOLDBEAM_USE_GDAL' in os.environ:
    reproject_rasters = _gdal_reproject_rasters
