import logging

from .base import BaseResource
from .map import MapCollection
from .layer import LayerCollection

class User(BaseResource):
    def __init__(self, *args):
        super(User, self).__init__(*args)
        self.username = None
        self.maps = MapCollection()
        self.layers = LayerCollection()

    def on_get(self, resource):
        if 'username' in resource:
            self.username = resource['username']

        if 'resources' in resource:
            rs = resource['resources']
            if 'map_collection' in rs and 'url' in rs['map_collection']:
                self.maps.set_resource_url(rs['map_collection']['url']).get()
            if 'layer_collection' in rs and 'url' in rs['layer_collection']:
                self.layers.set_resource_url(rs['layer_collection']['url']).get()
