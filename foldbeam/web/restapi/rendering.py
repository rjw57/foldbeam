import math
import uuid

from flask import make_response
import mapnik

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

    map_srs = '+proj=merc +lon_0=0 +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs'
    map_extent = (-20037508.3428, -15496570.7397, 20037508.3428, 18764656.2314)

#        map_srs = '+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy +datum=OSGB36 +units=m +no_defs'
#        map_extent = (1393.0196, 13494.9764, 671196.3657, 1230275.0454)
#        map_extent = (457900, 193700, 458000, 194700)

#        map_srs = '+proj=lcc +lat_1=40 +lat_0=40 +lon_0=0 +k_0=0.9988085293 +x_0=600000 +y_0=600000 +a=6378298.3 +b=6356657.142669561 +pm=madrid +units=m +no_defs'
#        map_extent = (93568.0098, 169918.9449, 1227661.0463, 1043747.4891)

    tile_size = max(map_extent[2]-map_extent[0], map_extent[3]-map_extent[1]) * math.pow(2.0, -zoom)
    tile_box = mapnik.Box2d(
            map_extent[0] + tile_size * x,
            map_extent[1] + tile_size * y,
            map_extent[0] + tile_size * (x+1),
            map_extent[1] + tile_size * (y+1)
    )

    mapnik_map = mapnik.Map(256, 256, map_srs)
    mapnik_map.background = mapnik.Color(127,127,127,255)

    for layer in map_.layers:
        if layer.bucket is None:
            continue

        b = layer.bucket.bucket
        if len(b.layers) == 0:
            continue

        # FIXME: get layer by name!
        for source_layer in b.layers:
            if source_layer.spatial_reference is None:
                continue

            style = mapnik.Style()

            rule = mapnik.Rule()

            if source_layer.type is bucket.Layer.VECTOR_TYPE:
                poly = mapnik.PolygonSymbolizer()
                poly.fill = mapnik.Color(127,0,0,127)
                rule.symbols.append(poly)
            elif source_layer.type is bucket.Layer.RASTER_TYPE:
                rule.symbols.append(mapnik.RasterSymbolizer())

            style.rules.append(rule)

            style_name = 'style_%s' % (uuid.uuid4().hex)
            mapnik_map.append_style(style_name, style)

            mapnik_layer = mapnik.Layer(str(layer.name), source_layer.spatial_reference.ExportToProj4())
            mapnik_layer.datasource = source_layer.mapnik_datasource
            mapnik_layer.styles.append(style_name)
            mapnik_map.layers.append(mapnik_layer)

    mapnik_map.zoom_to_box(tile_box)

    im = mapnik.Image(mapnik_map.width, mapnik_map.height)
    mapnik.render(mapnik_map, im)
    
    response = make_response(im.tostring('png'))
    response.headers['Content-Type'] = 'image/png'

    return response
