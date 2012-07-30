import itertools
import urlparse

from tornado.web import RequestHandler, removeslash

from foldbeam.web import model

class BaseHandler(RequestHandler):
    """A base class for all handlers. This contains utility methods to return
    the resource URL for various model objects.
    
    """
    def set_default_headers(self):
        # Support CORS
        if 'Origin' in self.request.headers:
            self.set_header('Access-Control-Allow-Origin', self.request.headers['Origin'])
            self.set_header('Access-Control-Allow-Headers', 'Content-Type')
            self.set_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE')

    def options(self, *args):
        pass

    def user_url(self, user):
        return urlparse.urljoin(self.request.full_url(), self.reverse_url('user', user.username))

    def map_collection_url(self, user):
        return urlparse.urljoin(self.request.full_url(), self.reverse_url('map_collection', user.username))

    def map_url(self, map_):
        return urlparse.urljoin(self.request.full_url(), self.reverse_url('map', map_.owner.username, map_.map_id))

    def layer_collection_url(self, user, map_=None):
        if map_ is None:
            return urlparse.urljoin(self.request.full_url(),
                    self.reverse_url('layer_collection', user.username))
        return urlparse.urljoin(self.request.full_url(),
                self.reverse_url('map_layer_collection', user.username, map_.map_id))

    def layer_url(self, layer):
        return urlparse.urljoin(self.request.full_url(),
                self.reverse_url('layer', layer.owner.username, layer.layer_id))

    def get_user_or_404(self, username):
        try:
            return model.User.from_name(username)
        except KeyError as e:
            self.send_error(404)

    def get_map_or_404(self, map_id):
        try:
            return model.Map.from_id(map_id)
        except KeyError as e:
            self.send_error(404)

    def get_layer_or_404(self, layer_id):
        try:
            return model.Layer.from_id(layer_id)
        except KeyError as e:
            self.send_error(404)

class BaseCollectionHandler(BaseHandler):
    def get_collection(self, offset, limit, *args):
        return None                 # pragma: no cover

    def item_resource(self, item):
        raise NotImplementedError   # pragma: no cover

    @removeslash
    def get(self, username, *args):
        offset = 0
        limit = 10

        items = self.get_collection(offset, limit, username, *args)
        if items is None:
            self.send_error(404)
            return

        response = {
            'resources': list(itertools.imap(self.item_resource, items)),
            'window': { 'limit': limit, 'offset': offset },
        }

        self.write(response)
