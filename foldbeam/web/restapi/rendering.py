import math
import StringIO
import uuid

import cairo
from PIL import Image
from flask import make_response

from foldbeam import bucket
from .flaskapp import app, resource
from .util import *

@app.route('/<username>/maps/<map_id>/tms')
def map_tms_tile_base(username, map_id):
    user, map_ = get_user_and_map_or_404(username, map_id)
    return url_for_map_tms_tiles(map_)

@app.route('/<username>/maps/<map_id>/tms/<int:zoom>/<int:x>/<int:y>.png')
def map_tms_tile(username, map_id, zoom, x, y):
    user, map_ = get_user_and_map_or_404(username, map_id)

    output_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 256, 256)
    context = cairo.Context(output_surface)

    for layer in map_.layers:
        if layer.bucket is None:
            continue

        source_layer = layer.source
        if source_layer is None:
            continue

        map_srs = map_.srs
        map_extent = map_.extent

        tile_size = max(map_extent[2]-map_extent[0], map_extent[3]-map_extent[1]) * math.pow(2.0, -zoom)
        tile_box = (
                map_extent[0] + tile_size * x,
                map_extent[1] + tile_size * y,
                map_extent[0] + tile_size * (x+1),
                map_extent[1] + tile_size * (y+1)
        )

        source_layer.render_to_cairo_context(context, map_srs, tile_box, (256, 256))

    im = Image.frombuffer('RGBA', (output_surface.get_width(), output_surface.get_height()), output_surface.get_data(), 'raw', 'BGRA', 0, 1)
    out = StringIO.StringIO()
    im.save(out, 'png')

    response = make_response(out.getvalue())
    response.headers['Content-Type'] = 'image/png'
    return response
