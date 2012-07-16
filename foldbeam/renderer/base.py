import os

import cairo

_data_dir = os.path.join(os.path.dirname(__file__), 'data')

_placeholder_surface = None
def _get_placeholder_surface():
    global _placeholder_surface
    if _placeholder_surface is not None:
        return _placeholder_surface
    _placeholder_surface = cairo.ImageSurface.create_from_png(
            os.path.join(_data_dir, 'placeholder.png'))
    return _placeholder_surface

def set_geo_transform(context, left, right, top, bottom, device_width, device_height):
    """Apply a geo transform to a cairo context.

    This is a convenience function to make it easy to map a desired output extent onto an output surface. Calling this
    with the desired top, left, bottom and right co-ordinates corresponding to the rectangular extent of a surface will
    append the appropriate transformation matrix to the cairo context.

    If the top-left of the context was (0,0) and the bottom right was (device_width, device_height), after this the
    top-left is (left, top) and bottom-right is (right, bottom).

    :param context: the cairo context to transform
    :param left: the left co-ordinate
    :param right: the right co-ordinate
    :param top: the top co-ordinate
    :param bottom: the bottom co-ordinate
    :param device_width: the width of the underlying device
    :param device_height: the height of the underlying device
    """

    context.scale(float(device_width) / float(right - left), float(device_height) / float(bottom - top))
    context.translate(-left, -top)

class RendererBase(object):
    """The base class for all renderers. A renderer can take a cairo surface and render into it. The surface's
    user-space co-ordinate system specifies the extent to render. The :py:meth:`render` method optionally takes a
    spatial reference allowing implicit transformation of the underlying data if necessary.
    
    """

    def render(self, context, spatial_reference=None):
        """Called to render the object to the specified cairo context.

        The user co-ordinates of the cairo context are respected. If you want to render a specific portion of the image,
        translate and scale the user co-ordinate system appropriately.

        The output context's co-ordinate system optionally has a spatial reference associated with it. If this is not
        specified, it is assumed that the 'natural' spatial reference of the renderer object will be used. This is
        generally a bad idea; unless you know what you're doing always specify the :py:obj:`spatial_reference`
        parameter.

        :param context: the cairo context to render this object to
        :param spatial_reference: default None, the spatial reference for the context's user co-ordinate system
        :type spatial_reference: osgeo.osr.SpatialReference or None
        """

        # Get the user space distance of one output device unit
        placeholder_scale = max(*[abs(x) for x in context.user_to_device_distance(1, 1)])

        context.set_source_surface(_get_placeholder_surface())
        context.get_source().set_extend(cairo.EXTEND_REPEAT)
        context.get_source().set_matrix(cairo.Matrix(xx=placeholder_scale, yy=-placeholder_scale))
        context.paint()

