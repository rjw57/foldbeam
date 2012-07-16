import math

import cairo

from foldbeam.core import RendererBase, Envelope
from foldbeam.core import boundary_from_envelope

class GeometryRenderer(RendererBase):
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

    """
    def __init__(self, **kwargs):
        super(GeometryRenderer, self).__init__()
        self.geom = None
        self.marker_radius = 5
        self.stroke = True
        self.fill = False

        for k, v in kwargs.iteritems():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                raise AttributeError(k)

    def render(self, context, spatial_reference=None):
        if self.geom is None:
            return

        if not self.stroke and not self.fill:
            return

        minx, miny, maxx, maxy = context.clip_extents()
        boundary = boundary_from_envelope(Envelope(minx, maxx, maxy, miny, spatial_reference))

        for g in self.geom.within(boundary, spatial_reference):
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

    def _stroke_and_or_fill(self, context):
        if self.fill and not self.stroke:
            context.fill()
        elif self.fill and self.stroke:
            context.fill_preserve()
            context.stroke()
        elif self.stroke:
            context.stroke()

    def _render_point(self, p, context):
        context.arc(p.x, p.y, self.marker_radius, 0, math.pi * 2.0)
        self._stroke_and_or_fill(context)

    def _path(self, ls, context, close_path=False):
        xs, ys = ls.xy
        if len(xs) == 0:
            return
        context.move_to(xs[0], ys[0])
        for x, y in zip(xs[1:], ys[1:]):
            context.line_to(x, y)
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

