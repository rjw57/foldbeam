import logging
import math
import os

from PIL import Image
import numpy as np

logging.basicConfig(level=logging.INFO)

def surface_hash(surface):
    """Return a hash of the data within a Cairo ImageSurface. This is a quasi-perceptual hash based off of the image
    histogram. It wont detect slightly different images but should detect massively different ones.
    
    This 'hash' is actually the image entropy rounded up to the nearest bit."""

    # extract the surface data into an image
    im = Image.frombuffer('RGBA', (surface.get_width(), surface.get_height()), surface.get_data(), 'raw', 'BGRA', 0, 1)

    # compute the histogram (ignoring zeros)
    hist = np.array([x for x in im.histogram() if x != 0], dtype=np.float)

    # normalise the histogram -> probability
    norm = np.sum(hist)
    hist = hist / norm

    # compute entropy per pixel
    entropy = - np.sum(hist[hist != 0] * np.log2(hist[hist != 0]))

    # multiply per-pixel entropy by number of pixels
    entropy *= norm

    return int(math.ceil(entropy))

def output_surface(surface, name):
    if not os.path.isdir('test-output'):
        os.mkdir('test-output')
    surface.write_to_png(os.path.join('test-output', name + '.png'))
