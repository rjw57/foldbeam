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
            if 'maps' in rs and 'url' in rs['maps']:
                self.maps.set_resource_url(rs['maps']['url'])
            if 'layers' in rs and 'url' in rs['layers']:
                self.layers.set_resource_url(rs['layers']['url'])
