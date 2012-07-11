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

    :param context: the cairo context to transform
    :param left: the left co-ordinate
    :param right: the right co-ordinate
    :param top: the top co-ordinate
    :param bottom: the bottom co-ordinate
    :param device_width: the width of the underlying device
    :param device_height: the height of the underlying device
    """

    context.scale(float(device_width) / float(right - left), float(device_height) / float(top - bottom))
    context.translate(left, bottom)

class RendererBase(object):
    def render(self, context):
        """Called to render the object to the specified cairo context.

        The user co-ordinates of the cairo context are respected. If you want to render a specific portion of the image,
        translate and scale the user co-ordinate system appropriately.

        :param context: the cairo context to render this object to
        """

        # Get the user space distance of one output device unit
        placeholder_scale = max(*context.user_to_device_distance(1, 1))

        context.set_source_surface(_get_placeholder_surface())
        context.get_source().set_extend(cairo.EXTEND_REPEAT)
        context.get_source().set_matrix(cairo.Matrix(placeholder_scale, 0.0, 0.0, placeholder_scale, 0.0, 0.0))
        context.paint()
