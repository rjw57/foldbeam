import math
import uuid

from flask import make_response
import mapnik

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


    mapnik_map = mapnik.Map(256, 256, map_srs)
    mapnik_map.maximum_extent = mapnik.Box2d(*map_extent)
    mapnik_map.background = mapnik.Color(0,0,0,0)

    im = mapnik.Image(mapnik_map.width, mapnik_map.height)

    if layer.bucket is None:
        response = make_response(im.tostring('png'))
        response.headers['Content-Type'] = 'image/png'
        return response

    source_layer = layer.source
    if source_layer is None:
        response = make_response(im.tostring('png'))
        response.headers['Content-Type'] = 'image/png'
        return response

    for source_layer in layer.bucket.bucket.layers:
        if source_layer.spatial_reference is None:
            continue

        style = mapnik.Style()

        rule = mapnik.Rule()

        subtype = source_layer.subtype
        if source_layer.type is bucket.Layer.VECTOR_TYPE:
            if subtype is bucket.Layer.POLYGON_SUBTYPE or subtype is bucket.Layer.MULTIPOLYGON_SUBTYPE:
                symb = mapnik.PolygonSymbolizer()
                symb.fill = mapnik.Color(127,0,0,127)
                rule.symbols.append(symb)
            elif subtype is bucket.Layer.POINT_SUBTYPE or subtype is bucket.Layer.MULTIPOINT_SUBTYPE:
                symb = mapnik.PointSymbolizer()
                rule.symbols.append(symb)
            elif subtype is bucket.Layer.LINESTRING_SUBTYPE or subtype is bucket.Layer.MULTILINESTRING_SUBTYPE:
                symb = mapnik.LineSymbolizer()
                stroke = mapnik.Stroke()
                stroke.color = mapnik.Color(0,127,0,127)
                stroke.width = 2
                symb.stroke = stroke
                rule.symbols.append(symb)
            else:
                continue
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
    mapnik.render(mapnik_map, im)
    
    response = make_response(im.tostring('png'))
    response.headers['Content-Type'] = 'image/png'
    return response
