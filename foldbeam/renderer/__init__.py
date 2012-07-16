"""Support for rendering directly to Cairo surfaces for display to the user.

"""
import sys

from foldbeam.renderer.base import *
from foldbeam.renderer.decorator import *
from foldbeam.renderer.geometry_renderer import *
from foldbeam.renderer.tile_fetcher import *

# This does some magic manipulation of the __module__ attribute for the things we just imported so that they appear to
# have come from this module. This is mostly so that Sphinx's autodoc will pull them in.
for k, v in sys.modules[__name__].__dict__.items():
    if not hasattr(v, '__module__'):
        continue
    if v.__module__.startswith(__name__ + '.'):
        v.__module__ = __name__

import TileStache

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
        self.renderer.render(cr, spatial_reference=spatial_reference)

        im = Image.frombuffer('RGBA', (width, height), surface.get_data(), 'raw', 'BGRA', 0, 1)
        return im
