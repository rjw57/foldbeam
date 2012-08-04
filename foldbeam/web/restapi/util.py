import functools
import urlparse

from flask import abort, request, url_for

from foldbeam.web import model

def _url_for(name, **kwargs):
    return urlparse.urljoin(request.base_url, url_for(name, **kwargs))

def urn_for_map(map_):
    return 'urn:uuid:' + map_.map_id

def urn_for_layer(layer):
    return 'urn:uuid:' + layer.layer_id

def get_layer_for_urn(layer_urn):
    """:raises KeyError: when urn is invalid."""
    layer_id = layer_urn.rsplit(':',1)[-1]
    return model.Layer.from_id(layer_id)

def urn_for_bucket(bucket):
    return 'urn:uuid:' + bucket.bucket_id

def get_bucket_for_urn(bucket_urn):
    """:raises KeyError: when urn is invalid."""
    bucket_id = bucket_urn.rsplit(':',1)[-1]
    return model.Bucket.from_id(bucket_id)

def url_for_user(user):
    return _url_for('user', username=user.username)

def url_for_user_maps(user):
    return _url_for('maps', username=user.username)

def url_for_user_layers(user):
    return _url_for('layers', username=user.username)

def url_for_user_buckets(user):
    return _url_for('buckets', username=user.username)

def url_for_map(map_):
    return _url_for('map', username=map_.owner.username, map_id=map_.map_id)

def url_for_map_layers(map_):
    return _url_for('map_layers', username=map_.owner.username, map_id=map_.map_id)

def url_for_map_layer(map_, layer):
    return _url_for('map_layer', username=map_.owner.username, map_id=map_.map_id, layer_id=layer.layer_id)

def url_for_map_tms_tiles(map_):
    return _url_for('map_tms_tile_base', username=map_.owner.username, map_id=map_.map_id)

def url_for_layer(layer):
    return _url_for('layer', username=layer.owner.username, layer_id=layer.layer_id)

def url_for_bucket(bucket):
    return _url_for('bucket', username=bucket.owner.username, bucket_id=bucket.bucket_id)

def url_for_bucket_files(bucket):
    return _url_for('bucket_files', username=bucket.owner.username, bucket_id=bucket.bucket_id)

def url_for_bucket_file(bucket, filename):
    return _url_for('bucket_file', username=bucket.owner.username, bucket_id=bucket.bucket_id, filename=filename)

def get_user_or_404(username):
    try:
        return model.User.from_name(username)
    except KeyError:
        abort(404)

def get_map_or_404(map_id):
    try:
        return model.Map.from_id(map_id)
    except KeyError:
        abort(404)

def get_layer_or_404(layer_id):
    try:
        return model.Layer.from_id(layer_id)
    except KeyError:
        abort(404)

def get_bucket_or_404(bucket_id):
    try:
        return model.Bucket.from_id(bucket_id)
    except KeyError:
        abort(404)

def get_user_and_map_or_404(username, map_id):
    user = get_user_or_404(username)
    map_ = get_map_or_404(map_id)
    if not map_.is_owned_by(user):
        abort(404)
    return user, map_

def get_user_and_layer_or_404(username, layer_id):
    user = get_user_or_404(username)
    layer = get_layer_or_404(layer_id)
    if not layer.is_owned_by(user):
        abort(404)
    return user, layer

def get_user_and_bucket_or_404(username, bucket_id):
    user = get_user_or_404(username)
    bucket = get_bucket_or_404(bucket_id)
    if not bucket.is_owned_by(user):
        abort(404)
    return user, bucket

def ensure_json(f):
    """A decorator which ensures that the request.json attribute is non-None. If it is None, the request is aborted with
    status code 400 (Bad Request).

    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if request.json is None:
            abort(400) # Bad request
        return f(*args, **kwargs)
    return wrapper
        
def update_map(m, request):
    """Given a decoded request, update an existing map from it."""
    if 'name' in request:
        m.name = request['name']
        
def update_layer(l, request):
    """Given a decoded request, update an existing layer from it."""
    if 'name' in request:
        l.name = request['name']

    if 'source' in request:
        s = request['source']
        if 'bucket' in s:
            l.bucket = get_bucket_for_urn(s['bucket'])
        if 'source' in s:
            l.bucket_layer_name = s['source']

#    if 'bucket' in request:
#        bucket = model.Bucket.from_id(request['bucket'])
#        assert bucket is not None
#        l.bucket = bucket
        
def update_bucket(b, request):
    """Given a decoded request, update an existing bucket from it."""
    if 'name' in request:
        b.name = request['name']

