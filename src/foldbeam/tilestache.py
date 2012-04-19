from nodes import *
from core import Envelope
from pads import ContentType
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
                'aerial': {
                    'provider': {
                        'name': 'proxy', 
                        'provider': 'MICROSOFT_AERIAL',
                    },
                },
                'ms-road': {
                    'provider': {
                        'name': 'proxy', 
                        'provider': 'MICROSOFT_ROAD',
                    },
                },
                'ms-aerial': {
                    'provider': {
                        'name': 'proxy', 
                        'provider': 'MICROSOFT_AERIAL',
                    },
                },
                'yahoo-road': {
                    'provider': {
                        'name': 'proxy', 
                        'provider': 'YAHOO_ROAD',
                    },
                },
                'yahoo-aerial': {
                    'provider': {
                        'name': 'proxy', 
                        'provider': 'YAHOO_AERIAL',
                    },
                },
            },
        })
        tiff_path = os.path.join(os.path.dirname(__file__), '..', '..', 'examples')

        os_tiles = [
                gdal.Open(os.path.join(tiff_path, 'raster-250k_17007/'+x+'-expanded.tif'))
                for x in ('su', 'so', 'sp', 'st')
        ]

        proj = SpatialReference()
        proj.ImportFromEPSG(27700)
        for t in os_tiles:
            t.SetProjection(proj.ExportToWkt())

        os_nodes = [GDALDatasetRasterNode(x) for x in os_tiles]
#        os_nodes = [ToRgbaRasterNode(x.output) for x in os_nodes]

        nodes, opacities = zip(*\
            [
                (TileStacheRasterNode(self.config.layers['ms-aerial']), 1),
            ] + \
            [
#                (GDALDatasetRasterNode(gdal.Open(os.path.join(tiff_path, 'dtm21.tif'))), 1),
#                (GDALDatasetRasterNode(gdal.Open(os.path.join(tiff_path, 'ASTGTM2_N51W002_dem.tif'))), 1),
#                (GDALDatasetRasterNode(gdal.Open(os.path.join(tiff_path, 'sp30se.tif'))), 1),
#                (GDALDatasetRasterNode(gdal.Open(os.path.join(tiff_path, 'sp30sw.tif'))), 1),
            ] + \
            [ (x, 0.6) for x in os_nodes ] + \
            [ (TileStacheRasterNode(self.config.layers['ms-road']), 0.5), ]
        )
        self.node = LayerRasterNode([node.output for node in nodes], opacities)

    def renderArea(self, width, height, srs, xmin, ymin, xmax, ymax, zoom):
        spatial_reference = osr.SpatialReference()
        spatial_reference.ImportFromProj4(srs)
        envelope = Envelope(xmin, xmax, ymax, ymin, spatial_reference)

        type_, raster = self.node.output(envelope, (width, height))
        if type_ == ContentType.NONE:
            return Image.new('RGBA', (width, height))

        assert type_ == ContentType.RASTER
        rgba = raster.to_rgba()
        if rgba is not None:
            return Image.fromarray(np.uint8(255.0 * np.clip(rgba, 0.0, 1.0)))

        return Image.new('L', (width, height))

