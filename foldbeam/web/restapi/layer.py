import itertools

from tornado.web import removeslash

from foldbeam.web import model

from .base import BaseHandler, BaseCollectionHandler
from .util import decode_request_body, update_layer

class LayerCollectionHandler(BaseCollectionHandler):
    def get_collection(self, offset, limit, username, map_id=None):
        try:
            user = model.User.from_name(username)
        except KeyError:
            return None

        if map_id is None:
            return itertools.islice(user.layers, offset, offset+limit)
        
        try:
            map_ = model.Map.from_id(map_id)
        except KeyError:
            return None

        if not map_.is_owned_by(user):
            return None

        return itertools.islice(map_.layers, offset, offset+limit)

    def item_resource(self, item):
        return {
            'url': self.layer_url(item),
            'name': item.name,
            'uuid': item.layer_id,
        }

    @decode_request_body
    @removeslash
    def post(self, username, map_id=None):
        user = self.get_user_or_404(username)
        if user is None:
            return

        map_ = None
        if map_id is not None:
            map_ = self.get_map_or_404(map_id)
            if map_ is None:
                return None

            if not map_.is_owned_by(user):
                self.send_error(404)
                return None

        # Create a new layer
        l = model.Layer(user)
        update_layer(l, self.request.body)
        l.save()

        if map_ is not None:
            map_.layer_ids.append(l.layer_id)
            map_.save()

        # Return it
        self.set_status(201)
        self.set_header('Location', self.layer_url(l))
        self.write({ 'url': self.layer_url(l) })

class LayerHandler(BaseHandler):
    def write_layer_resource(self, layer):
        self.write(self.layer_resource(layer))

    def layer_resource(self, layer):
        return {
            'name': layer.name,
            'owner': { 'url': self.user_url(layer.owner), 'username': layer.owner.username },
            'tiles': layer.tiles,
            'uuid': layer.layer_id,
        }

    def get(self, username, layer_id):
        user = self.get_user_or_404(username)
        if user is None:
            return

        layer = self.get_layer_or_404(layer_id)
        if layer is None:
            return

        if layer.owner.username != user.username:
            self.send_error(404)
            return

        self.write_layer_resource(layer)

    @decode_request_body
    def post(self, username, layer_id):
        try:
            user = model.User.from_name(username)
        except KeyError as e:
            self.send_error(404)
            return

        m = self.get_layer_or_404(layer_id)
        if not m.is_owned_by(user):
            self.send_error(404)
            return

        update_layer(m, self.request.body)
        m.save()

        self.set_status(201)
        self.set_header('Location', self.layer_url(m))
        self.write({ 'url': self.layer_url(m) })
