from nodes import *
from core import Envelope
from graph import ContentType
from PIL import Image
from TileStache import *
import os
from osgeo import osr, gdal
import numpy as np

class NodeProvider(object):
    """A very preliminary example of acting as a TileStache tile provider."""

    def __init__(self, layer):
        self.layer = layer

        cache_dir = os.path.join(os.path.dirname(__file__), 'tile-cache')
        self.config = Config.buildConfiguration({
            'cache': {
                'name': 'Disk',
                'path': cache_dir,
            },
            'layers': {
                'osm': {
                    'provider': {
                        'name': 'proxy', 
                        'url': 'http://otile1.mqcdn.com/tiles/1.0.0/osm/{Z}/{X}/{Y}.png',
                    },
                },
            },
        })
        tiff_path = os.path.join(os.path.dirname(__file__), '..', '..')
        nodes = [
                TileStacheRasterNode(self.config.layers['osm']),
#                GDALDatasetRasterNode(gdal.Open(os.path.join(tiff_path, 'dtm21.tif'))),
#                GDALDatasetRasterNode(gdal.Open(os.path.join(tiff_path, 'ASTGTM2_N51W002_dem.tif'))),
#                GDALDatasetRasterNode(gdal.Open(os.path.join(tiff_path, 'sp30se.tif'))),
#                GDALDatasetRasterNode(gdal.Open(os.path.join(tiff_path, 'sp30sw.tif'))),
        ]
        self.node = LayerRasterNode([node.outputs['raster'] for node in nodes])

    def renderArea(self, width, height, srs, xmin, ymin, xmax, ymax, zoom):
        spatial_reference = osr.SpatialReference()
        spatial_reference.ImportFromProj4(srs)
        envelope = Envelope(xmin, xmax, ymax, ymin, spatial_reference)

        type_, raster = self.node.outputs['raster'](envelope, (width, height))
        if type_ == ContentType.NONE:
            return Image.new('RGBA', (width, height))

        assert type_ == ContentType.RASTER
        rgba = raster.to_rgba()
        if rgba is not None:
            return Image.fromarray(np.uint8(255.0 * np.clip(rgba, 0.0, 1.0)))

        return Image.new('L', (width, height))

