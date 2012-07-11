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

class RendererBase(object):
    def render(self, context):
        """Called to render the object to the specified cairo context.

        :param context: the cairo context to render this object to
        """

        context.set_source_surface(_get_placeholder_surface())
        context.get_source().set_extend(cairo.EXTEND_REPEAT)
        context.paint()
