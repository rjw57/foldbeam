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
