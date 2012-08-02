import itertools

from tornado.web import removeslash

import foldbeam.bucket
from foldbeam.web import model

from .base import BaseHandler, BaseCollectionHandler
from .util import decode_request_body, update_bucket

class BucketCollectionHandler(BaseCollectionHandler):
    def get_collection(self, offset, limit, username):
        try:
            user = model.User.from_name(username)
        except KeyError:
            return None
        return itertools.islice(user.buckets, offset, offset+limit)

    def item_resource(self, item):
        return {
            'url': self.bucket_url(item),
            'name': item.name,
            'uuid': item.bucket_id,
        }

    @decode_request_body
    @removeslash
    def post(self, username):
        user = self.get_user_or_404(username)
        if user is None:
            return

        # Create a new bucket
        b = model.Bucket(user)
        update_bucket(b, self.request.body)
        b.save()

        # Return it
        self.set_status(201)
        self.set_header('Location', self.bucket_url(b))
        self.write({ 'url': self.bucket_url(b) })

class BucketHandler(BaseHandler):
    def write_bucket_resource(self, bucket):
        self.write(self.bucket_resource(bucket))

    def bucket_resource(self, bucket):
        layers = {}
        for l in bucket.bucket.layers:
            d = {}

            if l.type == foldbeam.bucket.Layer.VECTOR_TYPE:
                d['type'] = 'vector'
            elif l.type == foldbeam.bucket.Layer.RASTER_TYPE:
                d['type'] = 'raster'
            else:
                # should not be reached
                assert false    # pragma: no coverage

            if l.spatial_reference is not None:
                d['spatial_reference'] = { 'proj': l.spatial_reference.ExportToProj4(), 'wkt': l.spatial_reference.ExportToWkt() }
            else:
                d['spatial_reference'] = None

            layers[l.name] = d

        files = {}
        for f in bucket.bucket.files:
            files[f] = { 'url': self.bucket_file_url(bucket, f) }

        return {
            'name': bucket.name,
            'owner': { 'url': self.user_url(bucket.owner), 'username': bucket.owner.username },
            'uuid': bucket.bucket_id,
            'files': files,
            'primary_file': bucket.bucket.primary_file_name,
            'layers': layers,
        }

    def get(self, username, bucket_id):
        user = self.get_user_or_404(username)
        if user is None:
            return

        bucket = self.get_bucket_or_404(bucket_id)
        if bucket is None:
            return

        if bucket.owner.username != user.username:
            self.send_error(404)
            return

        self.write_bucket_resource(bucket)

    @decode_request_body
    @removeslash
    def post(self, username, bucket_id):
        user = self.get_user_or_404(username)
        if user is None:
            return

        bucket = self.get_bucket_or_404(bucket_id)
        if bucket is None:
            return

        if bucket.owner.username != user.username:
            self.send_error(404)
            return

        update_bucket(bucket, self.request.body)
        bucket.save()

        # Return it
        self.set_status(201)
        self.set_header('Location', self.bucket_url(bucket))
        self.write({ 'url': self.bucket_url(bucket) })

class BucketFileHandler(BaseHandler):
    def put(self, username, bucket_id, filename):
        user = self.get_user_or_404(username)
        if user is None:
            return

        bucket = self.get_bucket_or_404(bucket_id)
        if bucket is None:
            return

        if bucket.owner.username != user.username:
            self.send_error(404)
            return

        import StringIO
        try:
            bucket.bucket.add(filename, StringIO.StringIO(self.request.body))
        except foldbeam.bucket.BadFileNameError:
            self.send_error(400) # Bad request
            return

        self.set_status(201)
        self.set_header('Location', self.bucket_file_url(bucket, filename))
        self.write({ 'url': self.bucket_file_url(bucket, filename) })
