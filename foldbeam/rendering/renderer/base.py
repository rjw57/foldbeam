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

    def render_callable(self, context, spatial_reference=None):
        """Return a callable which can be called to render the object to the specified cairo context.
        
        Calling this method will not modify the Cairo context but may perform an intensive operation to prepare for
        rendering (e.g. a database query). The callable returned from this method will modify the context and, if
        possible, should do as little work beyond rendering as possible. It is intended that this method be thread safe
        but that the callables returned will be called sequentially to perform the actual rendering.

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

        def f():
            context.set_source_surface(_get_placeholder_surface())
            context.get_source().set_extend(cairo.EXTEND_REPEAT)
            context.get_source().set_matrix(cairo.Matrix(xx=placeholder_scale, yy=-placeholder_scale))
            context.paint()

        return f

class Wrapped(RendererBase):
    """Wrap a renderer with, optionally, a pre- or post-called callable. Each callable is passed the cairo context the
    renderer is being called with and it is intended that these should set up the Cairo context appropriately. For
    example, they may set the Cairo line width or fill pattern.

    .. py:attribute:: renderer

        The renderer instance to wrap

    .. py:attribute:: pre

        The callable to call before the renderer's :py:meth:`render` method.

    .. py:attribute:: post

        The callable to call before the renderer's :py:meth:`render` method.

    """
    def __init__(self, renderer, pre=None, post=None):
        self.pre = pre
        self.post = post
        self.renderer = renderer

    def render_callable(self, context, spatial_reference=None):
        wrapped_cb = self.renderer.render_callable(context, spatial_reference=spatial_reference)

        def f():
            if self.pre is not None:
                self.pre(context)
            
            wrapped_cb()

            if self.post is not None:
                self.post(context)

        return f

class Layers(RendererBase):
    """Render multiple layers one after another. Note that the layers are rendered in the order they are in the sequence
    and so the first-most layer will be the bottom-most in the output.

    :param layers: the set of layers or `None`
    :type layers: None or a sequence of renderers

    .. py:attribute:: layers

        `None` or a sequence of renderers. If `None`, no rendering is performed. Otherwise the renderers are rendered
        `in their order within the sequence` one after each other.
    """
    def __init__(self, layers=None):
        self.layers = layers

    def render_callable(self, context, spatial_reference=None):
        if self.layers is None:
            return lambda: None

        callables = [l.render_callable(context, spatial_reference=spatial_reference) for l in self.layers]
        return lambda: [x() for x in callables]
