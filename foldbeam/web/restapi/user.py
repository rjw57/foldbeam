import json

from flask import url_for, make_response

from .flaskapp import app, resource
from .util import *

@app.route('/<username>', methods=['GET', 'PUT'])
def user(username):
    if request.method == 'GET':
        return get_user(username)
    elif request.method == 'PUT':
        return put_user(username)

    # should never be reached
    abort(500) # pragma: no coverage

@resource
def get_user(username):
    user = get_user_or_404(username)
    return {
        'username': user.username,
        'resources': {
            'maps': { 'url': url_for_user_maps(user) },
            'layers': { 'url': url_for_user_layers(user) },
            'buckets': { 'url': url_for_user_buckets(user) },
        },
    }

def put_user(username):
    # This will replace the one currently in the DB
    user = model.User(username)
    user.save()

    response = make_response(json.dumps({ 'url': url_for_user(user) }), 201)
    response.headers['Location'] = url_for_user(user)
    response.headers['Content-Type'] = 'application/json'
    return response
