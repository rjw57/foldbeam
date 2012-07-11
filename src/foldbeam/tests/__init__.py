import logging
import os

from PIL import Image
import numpy as np

logging.basicConfig(level=logging.INFO)

def surface_hash(surface):
    """Return a hash of the data within a Cairo ImageSurface. This is a quasi-perceptual hash based off of the image
    histogram. It wont detect slightly different images but should detect massively different ones."""

    im = Image.frombuffer('RGBA', (surface.get_width(), surface.get_height()), surface.get_data(), 'raw', 'BGRA', 0, 1)

    # quantise histogram and take sum of squares
    hist = np.array([int(x/10) for x in im.histogram()])
    return int(np.sqrt(np.sum(hist * hist)))

def output_surface(surface, name):
    if not os.path.isdir('test-output'):
        os.mkdir('test-output')
    surface.write_to_png(os.path.join('test-output', name + '.png'))
