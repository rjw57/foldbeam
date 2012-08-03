import json

from flask import url_for, make_response

from .flaskapp import app, resource
from .util import *

@app.route('/<username>/layers', methods=['GET', 'POST'])
def layers(username):
    if request.method == 'GET':
        return get_layers(username)
    elif request.method == 'POST':
        return post_layers(username)

    # should never be reached
    abort(500) # pragma: no coverage

@resource
def get_layers(username):
    user = get_user_or_404(username)
    resources = []
    for resource in user.layers:
        resources.append({
            'name': resource.name,
            'url': url_for_layer(resource),
            'urn': urn_for_layer(resource),
        })
    return {
            'owner': { 'username': user.username, 'url': url_for_user(user) },
            'resources': resources,
    }

def post_layers(username):
    user = get_user_or_404(username)

    # Create a new layer
    l = model.Layer(user)
    if request.json is not None:
        update_layer(l, request.json)
    l.save()

    # Return it
    response = make_response(json.dumps({ 'url': url_for_layer(l), 'urn': urn_for_layer(l) }), 201)
    response.headers['Location'] = url_for_layer(l)
    response.headers['Content-Type'] = 'application/json'
    return response

@app.route('/<username>/layers/<layer_id>', methods=['GET', 'PUT'])
def layer(username, layer_id):
    if request.method == 'GET':
        return get_layer(username, layer_id)
    elif request.method == 'PUT':
        return put_layer(username, layer_id)

    # should never be reached
    abort(500) # pragma: no coverage

@resource
def get_layer(username, layer_id):
    user, layer = get_user_and_layer_or_404(username, layer_id)
    return {
            'name': layer.name,
            'urn': urn_for_layer(layer),
            'owner': { 'username': user.username, 'url': url_for_user(user) },
    }

def put_layer(username, layer_id):
    user, l = get_user_and_layer_or_404(username, layer_id)
    if request.json is not None:
        update_layer(l, request.json)
    l.save()

    # Return it
    response = make_response(json.dumps({ 'url': url_for_layer(l), 'urn': urn_for_layer(l) }), 201)
    response.headers['Location'] = url_for_layer(l)
    response.headers['Content-Type'] = 'application/json'
    return response
