"""Method decorators suitable for renderers.

"""
from functools import wraps
import logging
import math

import cairo
import numpy as np
from osgeo import gdal, gdal_array
from osgeo.ogr import CreateGeometryFromWkt

from foldbeam.renderer.base import set_geo_transform

log = logging.getLogger()

class ProjectionError(Exception):
    pass

def reproject_from_native_spatial_reference(f):
    """Wrap a rendering method by reprojecting rasterised images from a renderer which can handle only one spatial
    reference.

    The object with the wrapped rendering method *must* have an attribute called :py:attr:`native_spatial_reference`
    which is an instance of :py:class:`osgeo.osr.SpatialReference` giving the native spatial reference for that renderer.

    """
    @wraps(f)
    def render_callable(self, context, spatial_reference=None, f=f, **kwargs):
        # Find the native spatial reference
        native_spatial_reference = self.native_spatial_reference
        assert(native_spatial_reference is not None)

        # If no spatial reference was specified, or if it matches the native one, just render directly
        if spatial_reference is None or spatial_reference.IsSame(native_spatial_reference):
            return f(self, context, native_spatial_reference, **kwargs)

        log.info('Reprojecting from native SRS:')
        log.info(native_spatial_reference.ExportToWkt())
        log.info('to:')
        log.info(spatial_reference.ExportToWkt())

        # Construct a polygon representing the current clip area's extent
        target_min_x, target_min_y, target_max_x, target_max_y = context.clip_extents()

        wkt = 'POLYGON ((%s))' % (
                ','.join(['%f %f' % x for x in [
                    (target_min_x,target_min_y),
                    (target_max_x,target_min_y),
                    (target_max_x,target_max_y),
                    (target_min_x,target_max_y),
                    (target_min_x,target_min_y)
                ]]),
        )
        geom = CreateGeometryFromWkt(wkt)
        geom.AssignSpatialReference(spatial_reference)

        # segmentise the geometry to the scale of one device pixel
        seg_len = min(*[abs(x) for x in context.device_to_user_distance(1,1)])
        geom.Segmentize(seg_len)

        # compute a rough resolution for the intermediate based on the segment length and clip extents
        intermediate_size = (
            int(math.ceil(abs(target_max_x - target_min_x) / seg_len)),
            int(math.ceil(abs(target_max_y - target_min_y) / seg_len)),
        )

        # transform the geometry to the native spatial reference
        old_opt = gdal.GetConfigOption('OGR_ENABLE_PARTIAL_REPROJECTION')
        gdal.SetConfigOption('OGR_ENABLE_PARTIAL_REPROJECTION', 'TRUE')
        err = geom.TransformTo(native_spatial_reference)
        gdal.SetConfigOption('OGR_ENABLE_PARTIAL_REPROJECTION', old_opt)
        if err != 0:
            raise ProjectionError('Unable to project boundary into target projection: ' + str(err))

        # get the envelope of the clip area in the native spatial reference
        native_min_x, native_max_x, native_min_y, native_max_y = geom.GetEnvelope()

        # create a cairo image surface for the intermediate
        intermediate_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, intermediate_size[0], intermediate_size[1])
        intermediate_context = cairo.Context(intermediate_surface)
        set_geo_transform(
                intermediate_context,
                native_min_x, native_max_x, native_max_y, native_min_y,
                intermediate_size[0], intermediate_size[1]
        )

        # render the intermediate
        f(self, intermediate_context, native_spatial_reference, **kwargs)()

        # get hold of the intermediate surface as a dataset
        intermediate_dataset = _image_surface_to_dataset(intermediate_surface)
        assert intermediate_dataset is not None
        intermediate_dataset.SetGeoTransform((
            native_min_x, (native_max_x-native_min_x) / float(intermediate_size[0]), 0.0, 
            native_max_y, 0.0, -(native_max_y-native_min_y) / float(intermediate_size[1]),
        ))

        # create an output dataset
        output_pixel_size = context.device_to_user_distance(1,1)
        output_width = int(math.ceil(abs(target_max_x - target_min_x) / abs(output_pixel_size[0])))
        output_height = int(math.ceil(abs(target_max_y - target_min_y) / abs(output_pixel_size[1])))
        driver = gdal.GetDriverByName('MEM')
        assert driver is not None
        output_dataset = driver.Create('', output_width, output_height, 4, gdal.GDT_Byte)
        assert output_dataset is not None
        output_dataset.SetGeoTransform((
            target_min_x, abs(output_pixel_size[0]), 0.0,
            target_max_y, 0.0, -abs(output_pixel_size[1]),
        ))

        # project intermediate into output
        gdal.ReprojectImage(
                intermediate_dataset, output_dataset,
                native_spatial_reference.ExportToWkt(), spatial_reference.ExportToWkt(),
                gdal.GRA_Bilinear
        )

        # create a cairo image surface for the output. This unfortunately necessitates a copy since the in-memory format
        # for a GDAL Dataset is not interleaved.
        output_array = np.transpose(output_dataset.ReadAsArray(), (1,2,0))
        output_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, output_width, output_height)
        surface_array = np.frombuffer(output_surface.get_data(), dtype=np.uint8)
        surface_array[:] = output_array.flat
        output_surface.mark_dirty()

        def f():
            # draw the transformed output to the context
            context.set_source_surface(output_surface)
            context.get_source().set_matrix(cairo.Matrix(
                xx = 1.0 / abs(output_pixel_size[0]),
                yy = -1.0 / abs(output_pixel_size[1]),
                x0 = -target_min_x / abs(output_pixel_size[0]),
                y0 = -target_max_y / -abs(output_pixel_size[1]),
            ))

            # draw the tile itself. We disable antialiasing because if the tile slightly overlaps an output
            # pixel we want the interpolation of the tile to do the smoothing, not the rasteriser
            context.save()
            context.set_antialias(cairo.ANTIALIAS_NONE)
            context.rectangle(target_min_x, target_min_y, target_max_x - target_min_x, target_max_y - target_min_y)
            context.fill()
            context.restore()

        return f

    return render_callable

def _image_surface_to_array(image_surface):
    """Return a numpy array pointing to a Cairo image surface

    """
    assert(image_surface.get_format() == cairo.FORMAT_ARGB32)
    array = np.frombuffer(image_surface.get_data(), np.uint8)
    array.shape = (image_surface.get_height(), image_surface.get_width(), 4)
    return array

def _image_surface_to_dataset(image_surface):
    """Return a GDAL dataset pointing to a Cairo image surface.

    You may still need to set the geo transform for the dataset

    """

    assert(image_surface.get_format() == cairo.FORMAT_ARGB32)

    # Firtly get the surface as an array
    image_array = _image_surface_to_array(image_surface)

    dataset = gdal_array.OpenArray(np.rollaxis(image_array, 2))
    dataset.GetRasterBand(1).SetColorInterpretation(gdal.GCI_BlueBand)
    dataset.GetRasterBand(2).SetColorInterpretation(gdal.GCI_GreenBand)
    dataset.GetRasterBand(3).SetColorInterpretation(gdal.GCI_RedBand)
    dataset.GetRasterBand(4).SetColorInterpretation(gdal.GCI_AlphaBand)

    return dataset
