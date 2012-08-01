from tornado.web import Application, URLSpec, RequestHandler

from foldbeam.web import model

from .user import UserHandler
from .map import MapCollectionHandler, MapHandler
from .layer import LayerCollectionHandler, LayerHandler
from .bucket import BucketCollectionHandler, BucketHandler, BucketFileHandler

def new_application(**kwargs):
    """Return a new tornado application which can handle the REST API. The
    dictionary *kwargs* is passed to the tornado.web.Application constructor as
    keyword arguments.

    """
    return Application([
        URLSpec(r"/([a-zA-Z][a-zA-Z0-9_.]+)", UserHandler, name='user'),
        URLSpec(r"/([a-zA-Z][a-zA-Z0-9_.]+)/map", MapCollectionHandler, name='map_collection'),
        URLSpec(r"/([a-zA-Z][a-zA-Z0-9_.]+)/map/", MapCollectionHandler),
        URLSpec(r"/([a-zA-Z][a-zA-Z0-9_.]+)/map/_uuid/([a-f0-9]+)", MapHandler, name='map'),
        URLSpec(r"/([a-zA-Z][a-zA-Z0-9_.]+)/map/_uuid/([a-f0-9]+)/layer",
            LayerCollectionHandler, name='map_layer_collection'),
        URLSpec(r"/([a-zA-Z][a-zA-Z0-9_.]+)/layer", LayerCollectionHandler, name='layer_collection'),
        URLSpec(r"/([a-zA-Z][a-zA-Z0-9_.]+)/layer/", LayerCollectionHandler),
        URLSpec(r"/([a-zA-Z][a-zA-Z0-9_.]+)/layer/_uuid/([a-f0-9]+)", LayerHandler, name='layer'),
        URLSpec(r"/([a-zA-Z][a-zA-Z0-9_.]+)/bucket", BucketCollectionHandler, name='bucket_collection'),
        URLSpec(r"/([a-zA-Z][a-zA-Z0-9_.]+)/bucket/", BucketCollectionHandler),
        URLSpec(r"/([a-zA-Z][a-zA-Z0-9_.]+)/bucket/_uuid/([a-f0-9]+)", BucketHandler, name='bucket'),
        URLSpec(r"/([a-zA-Z][a-zA-Z0-9_.]+)/bucket/_uuid/([a-f0-9]+)/([^/]+)", BucketFileHandler, name='bucket_file'),
    ], **kwargs)
