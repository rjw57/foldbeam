"""
Serving output via TileStache
=============================

"""

import json

import numpy as np
from osgeo import osr
from PIL import Image
import TileStache

from foldbeam import core, graph, raster

@graph.node
class TileStacheServerNode(graph.Node):
    def __init__(self):
        super(TileStacheServerNode, self).__init__()
        self.add_input('raster', raster.Raster)

        # Create the tilestache config
        self.config = TileStache.Config.buildConfiguration({
            'cache': { 'name': 'Test' },
        })
        self.config.layers['foldbeam'] = TileStache.Core.Layer(
            config=self.config,
            projection=TileStache.Geography.SphericalMercator(),
            metatile=TileStache.Core.Metatile(),
        )

        # Create the provider
        self.config.layers['foldbeam'].provider = NodeProvider(self.inputs.raster)

        self.wsgi_server = TileStache.WSGITileServer(self.config)

class NodeProvider(object):
    """A very preliminary example of acting as a TileStache tile provider."""

    def __init__(self, raster_pad):
        self.raster_pad = raster_pad

    def renderArea(self, width, height, srs, xmin, ymin, xmax, ymax, zoom):
        spatial_reference = osr.SpatialReference()
        spatial_reference.ImportFromProj4(srs)
        envelope = core.Envelope(xmin, xmax, ymax, ymin, spatial_reference)

        raster = self.raster_pad(envelope=envelope, size=(width, height))
        if raster is None:
            return Image.new('RGBA', (width, height))

        rgba = raster.to_rgba()
        if rgba is not None:
            return Image.fromarray(np.uint8(255.0 * np.clip(rgba, 0.0, 1.0)))

        return Image.new('L', (width, height))

