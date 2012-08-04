import json

from flask import url_for, make_response

import foldbeam.bucket

from .flaskapp import app, resource
from .util import *

@app.route('/<username>/buckets', methods=['GET', 'POST'])
def buckets(username):
    if request.method == 'GET':
        return get_buckets(username)
    elif request.method == 'POST':
        return post_buckets(username)

    # should never be reached
    abort(500) # pragma: no coverage

@resource
def get_buckets(username):
    user = get_user_or_404(username)
    resources = []
    for resource in user.buckets:
        resources.append({
            'name': resource.name,
            'url': url_for_bucket(resource),
            'urn': urn_for_bucket(resource),
        })
    return {
            'owner': { 'username': user.username, 'url': url_for_user(user) },
            'resources': resources,
    }

def post_buckets(username):
    user = get_user_or_404(username)

    # Create a new bucket
    m = model.Bucket(user)
    if request.json is not None:
        update_bucket(m, request.json)
    m.save()

    # Return it
    response = make_response(json.dumps({ 'url': url_for_bucket(m), 'urn': urn_for_bucket(m) }), 201)
    response.headers['Location'] = url_for_bucket(m)
    response.headers['Content-Type'] = 'application/json'
    return response

@app.route('/<username>/buckets/<bucket_id>', methods=['GET', 'PUT'])
def bucket(username, bucket_id):
    if request.method == 'GET':
        return get_bucket(username, bucket_id)
    elif request.method == 'PUT':
        return put_bucket(username, bucket_id)
    # should never be reached
    abort(500) # pragma: no coverage

@resource
def get_bucket(username, bucket_id):
    user, bucket = get_user_and_bucket_or_404(username, bucket_id)

    sources = {}
    for s in bucket.bucket.layers:
        if s.type == foldbeam.bucket.Layer.VECTOR_TYPE:
            type_ = 'vector'
        elif s.type == foldbeam.bucket.Layer.RASTER_TYPE:
            type_ = 'raster'
        else:
            # should not be reached
            abort(500)

        if s.subtype == foldbeam.bucket.Layer.UNKNOWN_SUBTYPE:
            subtype = 'unknown'
        elif s.subtype == foldbeam.bucket.Layer.MIXED_SUBTYPE:
            subtype = 'mixed'
        elif s.subtype == foldbeam.bucket.Layer.POLYGON_SUBTYPE:
            subtype = 'polygon'
        elif s.subtype == foldbeam.bucket.Layer.POINT_SUBTYPE:
            subtype = 'point'
        elif s.subtype == foldbeam.bucket.Layer.LINESTRING_SUBTYPE:
            subtype = 'linestring'
        elif s.subtype == foldbeam.bucket.Layer.MULTIPOLYGON_SUBTYPE:
            subtype = 'multipolygon'
        elif s.subtype == foldbeam.bucket.Layer.MULTIPOINT_SUBTYPE:
            subtype = 'multipoint'
        elif s.subtype == foldbeam.bucket.Layer.MULTILINESTRING_SUBTYPE:
            subtype = 'multilinestring'
        else:
            abort(500) # pragma: no coverage

        srs = None
        if s.spatial_reference is not None:
            srs = { 'proj': s.spatial_reference.ExportToProj4(), 'wkt': s.spatial_reference.ExportToWkt() }

        sources[s.name] = {
            'spatial_reference': srs,
            'type': type_,
        }

    return {
            'name': bucket.name,
            'urn': urn_for_bucket(bucket),
            'owner': { 'username': user.username, 'url': url_for_user(user) },
            'sources': sources,
            'resources': { 'files': { 'url': url_for_bucket_files(bucket), } },
    }

@ensure_json
def put_bucket(username, bucket_id):
    user, bucket = get_user_and_bucket_or_404(username, bucket_id)
    update_bucket(bucket, request.json)
    bucket.save()

    # Return it
    response = make_response(json.dumps({ 'url': url_for_bucket(bucket) }), 201)
    response.headers['Location'] = url_for_bucket(bucket)
    response.headers['Content-Type'] = 'application/json'
    return response

@app.route('/<username>/buckets/<bucket_id>/files')
@resource
def bucket_files(username, bucket_id):
    user, bucket = get_user_and_bucket_or_404(username, bucket_id)
    
    files = []
    for f in bucket.bucket.files:
        files.append({
            'url': url_for_bucket_file(bucket, f),
            'name': f,
        })
    return { 'resources': files }

@app.route('/<username>/buckets/<bucket_id>/files/<filename>', methods=['PUT'])
def bucket_file(username, bucket_id, filename):
    if request.method == 'PUT':
        return put_bucket_file(username, bucket_id, filename)
    # should never be reached
    abort(500) # pragma: no coverage

def put_bucket_file(username, bucket_id, filename):
    user, bucket = get_user_and_bucket_or_404(username, bucket_id)

    try:
        import StringIO
        bucket.bucket.add(filename, StringIO.StringIO(request.data))
    except foldbeam.bucket.BadFileNameError:
        abort(400)

    # Return it
    response = make_response(json.dumps({ 'url': url_for_bucket_file(bucket, filename) }), 201)
    response.headers['Location'] = url_for_bucket_file(bucket, filename)
    response.headers['Content-Type'] = 'application/json'
    return response
