from .core import Envelope
from .pipeline import Pipeline
from .graph import Node, node, RasterType
import json
import numpy as np
from osgeo import osr
from PIL import Image
import TileStache
from werkzeug.serving import run_simple

@node
class TileStacheServerNode(Node):
    def __init__(self):
        super(TileStacheServerNode, self).__init__()
        self.add_input('raster', RasterType)

class NodeProvider(object):
    """A very preliminary example of acting as a TileStache tile provider."""

    def __init__(self, layer):
        config = json.load(open('pipeline.json'))
        self.pipeline = Pipeline(config)

    def renderArea(self, width, height, srs, xmin, ymin, xmax, ymax, zoom):
        spatial_reference = osr.SpatialReference()
        spatial_reference.ImportFromProj4(srs)
        envelope = Envelope(xmin, xmax, ymax, ymin, spatial_reference)

        raster = self.pipeline.outputs.values()[0](envelope=envelope, size=(width, height))
        if raster is None:
            return Image.new('RGBA', (width, height))

        rgba = raster.to_rgba()
        if rgba is not None:
            return Image.fromarray(np.uint8(255.0 * np.clip(rgba, 0.0, 1.0)))

        return Image.new('L', (width, height))

