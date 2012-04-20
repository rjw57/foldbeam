import json
from nodes import *
from core import Envelope
from pipeline import Pipeline
from PIL import Image
from TileStache import *
import os
from osgeo import osr, gdal
import numpy as np

class NodeProvider(object):
    """A very preliminary example of acting as a TileStache tile provider."""

    def __init__(self, layer):
        config = json.load(open('pipeline.json'))
        self.pipeline = Pipeline(config)

    def renderArea(self, width, height, srs, xmin, ymin, xmax, ymax, zoom):
        spatial_reference = osr.SpatialReference()
        spatial_reference.ImportFromProj4(srs)
        envelope = Envelope(xmin, xmax, ymax, ymin, spatial_reference)

        raster = self.pipeline.output(envelope=envelope, size=(width, height))
        if raster is None:
            return Image.new('RGBA', (width, height))

        rgba = raster.to_rgba()
        if rgba is not None:
            return Image.fromarray(np.uint8(255.0 * np.clip(rgba, 0.0, 1.0)))

        return Image.new('L', (width, height))

