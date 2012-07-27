import itertools

from tornado.web import removeslash

from foldbeam.web import model

from .base import BaseHandler, BaseCollectionHandler
from .util import decode_request_body, update_map

class MapCollectionHandler(BaseCollectionHandler):
    def get_collection(self, offset, limit, username):
        try:
            user = model.User.from_name(username)
        except KeyError:
            return None
        return itertools.islice(user.maps, offset, offset+limit)

    def item_resource(self, item):
        return {
            'url': self.map_url(item),
            'name': item.name,
            'uuid': item.map_id,
        }

    @decode_request_body
    @removeslash
    def post(self, username):
        user = self.get_user_or_404(username)
        if user is None:
            return

        # Create a new map
        m = model.Map(user)
        update_map(m, self.request.body)
        m.save()

        # Return it
        self.set_status(201)
        self.set_header('Location', self.map_url(m))
        self.write({ 'url': self.map_url(m) })

class MapHandler(BaseHandler):
    def write_map_resource(self, map_):
        self.write(self.map_resource(map_))

    def map_resource(self, map_):
        return {
            'name': map_.name,
            'owner': { 'url': self.user_url(map_.owner), 'username': map_.owner.username },
            'uuid': map_.map_id,
            'resources': {
                'layer_collection': {
                    'url': self.layer_collection_url(map_.owner, map_),
                },
            },
        }

    def get(self, username, map_id):
        user = self.get_user_or_404(username)
        if user is None:
            return

        map_ = self.get_map_or_404(map_id)
        if map_ is None:
            return

        if map_.owner.username != user.username:
            self.send_error(404)
            return

        self.write_map_resource(map_)

    @decode_request_body
    def post(self, username, map_id):
        try:
            user = model.User.from_name(username)
        except KeyError as e:
            self.send_error(404)
            return

        m = self.get_map_or_404(map_id)
        if not m.is_owned_by(user):
            self.send_error(404)
            return

        update_map(m, self.request.body)
        m.save()

        self.set_status(201)
        self.set_header('Location', self.map_url(m))
        self.write({ 'url': self.map_url(m) })
