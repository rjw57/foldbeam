import json

from flask import url_for, make_response

from .flaskapp import app, resource
from .util import *

@app.route('/<username>/maps', methods=['GET', 'POST'])
def maps(username):
    if request.method == 'GET':
        return get_maps(username)
    elif request.method == 'POST':
        return post_maps(username)

    # should never be reached
    abort(500) # pragma: no coverage

@resource
def get_maps(username):
    user = get_user_or_404(username)
    resources = []
    for resource in user.maps:
        resources.append({
            'name': resource.name,
            'url': url_for_map(resource),
            'urn': urn_for_map(resource),
        })
    return {
            'owner': { 'username': user.username, 'url': url_for_user(user) },
            'resources': resources,
    }

def post_maps(username):
    user = get_user_or_404(username)

    # Create a new map
    m = model.Map(user)
    if request.json is not None:
        update_map(m, request.json)
    m.save()

    # Return it
    response = make_response(json.dumps({ 'url': url_for_map(m), 'urn': urn_for_map(m) }), 201)
    response.headers['Location'] = url_for_map(m)
    response.headers['Content-Type'] = 'application/json'
    return response

@app.route('/<username>/maps/<map_id>', methods=['GET', 'PUT'])
def map(username, map_id):
    if request.method == 'GET':
        return get_map(username, map_id)
    elif request.method == 'PUT':
        return put_map(username, map_id)

    # should never be reached
    abort(500) # pragma: no coverage

@resource
def get_map(username, map_id):
    user, map_ = get_user_and_map_or_404(username, map_id)
    from osgeo import osr
    srs = osr.SpatialReference()
    srs.ImportFromProj4(map_.srs)

    layer_tiles = [url_for_map_tms_tiles(map_)]

    return {
            'name': map_.name,
            'urn': urn_for_map(map_),
            'owner': { 'username': user.username, 'url': url_for_user(user) },
            'resources': { 'layers': { 'url': url_for_map_layers(map_) }, },
            'layer_tiles': layer_tiles,
            'srs': { 'proj': srs.ExportToProj4(), 'wkt': srs.ExportToWkt() },
            'extent': map_.extent,
    }

@ensure_json
def put_map(username, map_id):
    user, m = get_user_and_map_or_404(username, map_id)

    update_map(m, request.json)
    m.save()

    # Return it
    response = make_response(json.dumps({ 'url': url_for_map(m), 'urn': urn_for_map(m) }), 201)
    response.headers['Location'] = url_for_map(m)
    response.headers['Content-Type'] = 'application/json'
    return response

@app.route('/<username>/maps/<map_id>/layers', methods=['GET', 'PUT'])
def map_layers(username, map_id):
    if request.method == 'GET':
        return get_map_layers(username, map_id)
    elif request.method == 'PUT':
        return put_map_layers(username, map_id)

    # should never be reached
    abort(500) # pragma: no coverage

@resource
def get_map_layers(username, map_id):
    user, map_ = get_user_and_map_or_404(username, map_id)
    resources = []
    for resource in map_.layers:
        resources.append({
            'name': resource.name,
            'urn': urn_for_layer(resource),
            'url': url_for_map_layer(map_, resource),
            'link_url': url_for_layer(resource),
        })
    return {
        'linked_resources': resources,
    }

@ensure_json
def put_map_layers(username, map_id):
    if not 'urn' in request.json:
        abort(400) # Bad request

    try:
        layer = get_layer_for_urn(request.json['urn'])
    except KeyError:
        abort(400) # Bad request

    user, m = get_user_and_map_or_404(username, map_id)
    m.add_layer(layer)
    m.save()

    # Return it
    response = make_response(json.dumps({ 'url': url_for_map_layer(m, layer), 'urn': urn_for_layer(layer) }), 201)
    response.headers['Location'] = url_for_map_layer(m, layer)
    response.headers['Content-Type'] = 'application/json'
    return response

@app.route('/<username>/maps/<map_id>/layers/<layer_id>', methods=['GET','DELETE','PUT'])
def map_layer(username, map_id, layer_id):
    if request.method == 'GET':
        return get_map_layer(username, map_id, layer_id)
    elif request.method == 'DELETE':
        return delete_map_layer(username, map_id, layer_id)
    elif request.method == 'PUT':
        return put_map_layer(username, map_id, layer_id)

    # should never be reached
    abort(500) # pragma: no coverage

@resource
def get_map_layer(username, map_id, layer_id):
    user, map_ = get_user_and_map_or_404(username, map_id)
    if not layer_id in map_.layer_ids:
        abort(404)
    layer = get_layer_or_404(layer_id)
    return { 'url': url_for_layer(layer), 'urn': urn_for_layer(layer), 'name': layer.name }

@resource
def delete_map_layer(username, map_id, layer_id):
    user, map_ = get_user_and_map_or_404(username, map_id)
    if not layer_id in map_.layer_ids:
        abort(404)
    layer = get_layer_or_404(layer_id)
    map_.remove_layer(layer)
    map_.save()
    return { 'status': 'ok' }

@resource
@ensure_json
def put_map_layer(username, map_id, layer_id):
    if 'index' not in request.json:
        abort(400) # Bad request

    try:
        index = int(request.json['index'])
    except ValueError:
        abort(400) # Bad request

    user, map_ = get_user_and_map_or_404(username, map_id)
    if not layer_id in map_.layer_ids:
        abort(404)
    layer = get_layer_or_404(layer_id)

    map_.move_layer(layer, index)
    map_.save()
    return { 'status': 'ok' }
