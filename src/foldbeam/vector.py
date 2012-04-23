from . import core, graph, pads
from .graph import connect
import cairo
import math
import numpy as np
from osgeo import ogr

class OgrDataSourceNode(graph.Node):
    def __init__(self, filename=None):
        super(OgrDataSourceNode, self).__init__()
        self.add_output('data_source', pads.CallableOutputPad(ogr.DataSource, lambda: self.data_source))
        self.add_input('filename', str, filename)
        self._data_source = None

    @property
    def filename(self):
        return self.inputs.filename()

    @property
    def data_source(self):
        if self._data_source is not None:
            return self._data_source
        fn = self.filename
        if fn is None:
            return None

        self._data_source = ogr.Open(fn)
        return self._data_source

class VectorRendererNode(graph.Node):
    def __init__(self, sql=None, filename=None, pen_rgba=None):
        super(VectorRendererNode, self).__init__()
        self.add_output('output', pads.CallableOutputPad(graph.RasterType, self._render))
        self.add_input('sql', str, sql)
        self.add_input('data_source', ogr.DataSource)
        self.add_input('pen_rgba', list, pen_rgba)

        if filename is not None:
            source = self.add_subnode(OgrDataSourceNode(filename))
            connect(source, 'data_source', self, 'data_source')

    @property
    def pen_rgba(self):
        c = self.inputs.pen_rgba()
        if len(c) == 3:
            return c + [1,]
        elif len(c) == 4:
            return c
        else:
            raise RuntimeError('Invalid pen_rgba: %s' % (c,))

    @property
    def sql(self):
        return self.inputs.sql()

    @property
    def data_source(self):
        return self.inputs.data_source()

    def _render(self, envelope, size):
        if self.sql is None or self.data_source is None:
            return None

        if size is None:
            size = map(int, envelope.size())

        # FIXME: Do transform!
        boundary = core.boundary_from_envelope(envelope)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size[0], size[1])

        cr = cairo.Context(surface)
        #cr.translate(-envelope.left, -envelope.right)
        #cr.scale(float(size[0]-1) / envelope.offset()[0], float(size[1]-1) / envelope.offset()[1])

        points = self.data_source.ExecuteSQL(self.sql, boundary.geometry)
        if points is None:
            return None

        feature = points.GetNextFeature()
        cr.set_source_rgba(*self.pen_rgba)
        while feature is not None:
            geom = feature.GetGeometryRef()
            pnt = geom.GetPoint(0)
            x, y = pnt[:2]

            px = (x - envelope.left) * (float(size[0]) / envelope.offset()[0])
            py = (y - envelope.top) * (float(size[1]) / envelope.offset()[1])

            rad = 2
            cr.move_to(px+rad, py)
            cr.arc(px, py, rad, 0.0, 2.0*math.pi)
            cr.fill()

            feature = points.GetNextFeature()

        print('Rendered %i features' % (len(points),))

        surface.flush()
        surface_array = np.frombuffer(surface.get_data(), dtype=np.uint8).reshape((size[1], size[0], 4), order='C')
        output = core.Raster(
            surface_array, envelope,
            to_rgba=core.RgbaFromBands(
            (
                (core.RgbaFromBands.BLUE,   1.0/255.0),
                (core.RgbaFromBands.GREEN,  1.0/255.0),
                (core.RgbaFromBands.RED,    1.0/255.0),
                (core.RgbaFromBands.ALPHA,  1.0/255.0),
            ), True)
        )

        return output
