"""Support for using a renderer as a provider with TileStache for serving slippy map tiles.
"""
import cairo
from osgeo.osr import SpatialReference
from PIL import Image
import TileStache

from foldbeam.renderer import TileFetcher, set_geo_transform

class TileStacheProvider(object):
    """An object suitable for use as a TileStache provider.

    .. py:attribute:: renderer

        Set this attribute to a renderer instance to use for rendering map tiles.
    """
    def __init__(self, layer):
        super(TileStacheProvider, self).__init__()
        self.renderer = TileFetcher()

    def renderArea(self, width, height, srs, xmin, ymin, xmax, ymax, zoom):
        spatial_reference = SpatialReference()

        # this is a special HACK to take account of the fact that the proj4 srs provided by TileStache has the +over
        # parameter and OGR thinks it is different to EPSG:3857
        if srs == TileStache.Geography.SphericalMercator.srs:
            spatial_reference.ImportFromEPSG(3857)
        else:
            spatial_reference.ImportFromProj4(srs)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        cr = cairo.Context(surface)
        set_geo_transform(cr, xmin, xmax, ymax, ymin, width, height)
        self.renderer.render_callable(cr, spatial_reference=spatial_reference)()

        im = Image.frombuffer('RGBA', (width, height), surface.get_data(), 'raw', 'BGRA', 0, 1)
        return im

