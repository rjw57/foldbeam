import math
import uuid

from flask import make_response

from foldbeam import bucket
from .flaskapp import app, resource
from .util import *

@app.route('/<username>/maps/<map_id>/layers/<layer_id>/tms')
def map_layer_tms_tile_base(username, map_id):
    user, map_ = get_user_and_map_or_404(username, map_id)
    return url_for_map_tms_tiles(map_)

@app.route('/<username>/maps/<map_id>/layers/<layer_id>/tms/<int:zoom>/<int:x>/<int:y>.png')
def map_layer_tms_tile(username, map_id, layer_id, zoom, x, y):
    user, map_ = get_user_and_map_or_404(username, map_id)
    if not layer_id in map_.layer_ids:
        abort(404)
    layer = get_layer_or_404(layer_id)

    if layer.bucket is None:
        abort(404)

    source_layer = layer.source
    if source_layer is None:
        abort(404)

    map_srs = map_.srs
    map_extent = map_.extent

    tile_size = max(map_extent[2]-map_extent[0], map_extent[3]-map_extent[1]) * math.pow(2.0, -zoom)
    tile_box = (
            map_extent[0] + tile_size * x,
            map_extent[1] + tile_size * y,
            map_extent[0] + tile_size * (x+1),
            map_extent[1] + tile_size * (y+1)
    )

    response = make_response(source_layer.render_png(map_srs, tile_box, (256, 256)))
    response.headers['Content-Type'] = 'image/png'
    return response
