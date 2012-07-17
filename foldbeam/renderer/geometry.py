import math

import cairo
import numpy as np

from foldbeam.core import Envelope
from foldbeam.core import boundary_from_envelope
from foldbeam.renderer import RendererBase

class Geometry(RendererBase):
    """Render shapely geometric shapes into a context.

    If keyword arguments are supplied, set the attributes listed below.

    .. py:attribute:: geom

        Default None. An object which yields a set of geometry to render. For example,
        :py:class:`foldbeam.geometry.IterableGeometry`.

    .. py:attribute:: marker_radius

        Default 5. The radius, in projection co-ordinates, of the point marker.

    .. py:attribute:: stroke

        Default True. If True, call 'stroke()' to draw the outline of geometry.

    .. py:attribute:: fill

        Default False. If True, call 'fill()' to fill the geometry. If both :py:attr:`fill` and :py:attr:`stroke` are
        True, then filling happens first.

    .. py:attribute:: prepare_stroke

        Default `None`. If not `None`, a callable which is called with a single argument of the cairo context to prepare
        it for a stroke operation.

    .. py:attribute:: prepare_fill

        Default `None`. If not `None`, a callable which is called with a single argument of the cairo context to prepare
        it for a fill operation.

    """
    def __init__(self, **kwargs):
        super(Geometry, self).__init__()
        self.geom = None
        self.marker_radius = 5
        self.stroke = True
        self.fill = False
        self.prepare_stroke = None
        self.prepare_fill = None

        for k, v in kwargs.iteritems():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                raise AttributeError(k)

    def render_callable(self, context, spatial_reference=None):
        if self.geom is None:
            return lambda: None

        if not self.stroke and not self.fill:
            return lambda: None

        minx, miny, maxx, maxy = context.clip_extents()
        boundary = boundary_from_envelope(Envelope(minx, maxx, maxy, miny, spatial_reference))

        geometry = self.geom.within(boundary, spatial_reference)

        def f():
            for g in geometry:
                if g.geom_type == 'Point':
                    self._render_point(g, context)
                elif g.geom_type == 'MultiPoint':
                    [self._render_point(x, context) for x in g]
                elif g.geom_type == 'LineString':
                    self._render_line_string(g, context)
                elif g.geom_type == 'MultiLineString':
                    [self._render_line_string(x, context) for x in g]
                elif g.geom_type == 'LinearRing':
                    self._render_line_string(g, context, close_path=True)
                elif g.geom_type == 'Polygon':
                    self._render_polygon(g, context)
                elif g.geom_type == 'MultiPolygon':
                    [self._render_polygon(x, context) for x in g]
                else:
                    log.warning('Unknown geometry type: ' + str(g.geom_type))

        return f

    def _stroke_and_or_fill(self, context):
        if self.fill and not self.stroke:
            if self.prepare_fill is not None:
                self.prepare_fill(context)
            context.fill()
        elif self.fill and self.stroke:
            if self.prepare_fill is not None:
                self.prepare_fill(context)
            context.fill_preserve()
            if self.prepare_stroke is not None:
                self.prepare_stroke(context)
            context.stroke()
        elif self.stroke:
            if self.prepare_stroke is not None:
                self.prepare_stroke(context)
            context.stroke()

    def _render_point(self, p, context):
        scale = max([abs(x) for x in context.device_to_user_distance(1,1)])
        context.arc(p.x, p.y, self.marker_radius * scale, 0, math.pi * 2.0)
        self._stroke_and_or_fill(context)

    def _path(self, ls, context, close_path=False):
        if ls.is_empty:
            return
        coords = np.asarray(ls)
        context.move_to(*coords[0,:2])
        for p in coords:
            context.line_to(*p[:2])
        if close_path:
            context.close_path()

    def _render_line_string(self, ls, context, close_path=False):
        self._path(ls, context, close_path)
        self._stroke_and_or_fill(context)

    def _render_polygon(self, ls, context):
        self._path(ls.exterior, context, True)
        for p in ls.interiors:
            self._path(p, context, True)
        context.save()
        context.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        self._stroke_and_or_fill(context)
        context.restore()

