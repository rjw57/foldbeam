from nodes import *
from core import Envelope
from graph import ContentType
from PIL import Image
from TileStache import *
import os
from osgeo import osr, gdal

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
        self.node = TileStacheRasterNode(self.config.layers['osm'])
        #self.node = GDALDatasetRasterNode(gdal.Open(os.path.join(os.path.dirname(__file__), '..', '..', 'dtm21.tif')))

    def renderArea(self, width, height, srs, xmin, ymin, xmax, ymax, zoom):
        spatial_reference = osr.SpatialReference()
        spatial_reference.ImportFromProj4(srs)
        envelope = Envelope(xmin, xmax, ymax, ymin, spatial_reference)
        type_, raster = self.node.outputs['raster'](envelope, (width, height))
        assert type_ == ContentType.RASTER

        ds = raster.dataset
        channels = [min(ds.RasterCount, i) for i in (1,2,3)]
        r, g, b = [ds.GetRasterBand(i).ReadRaster(0, 0, width, height) for i in channels]
        data = ''.join([''.join(pixel) for pixel in zip(r, g, b)])
        area = Image.fromstring('RGB', (width, height), data)
        return area
