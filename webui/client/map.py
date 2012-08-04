import logging

from .base import BaseResource
from .layer import LayerCollection

class Map(BaseResource):
    def __init__(self, *args):
        super(Map, self).__init__(*args)
        self.name = None
        self.layers = LayerCollection()
        self.tms_tile_base = None

    def on_get(self, resource):
        self.name = resource['name']
        self.layers.set_resource_url(resource['resources']['layers']['url'])
        self.tms_tile_base = resource['tms_tile_base']

class MapCollection(BaseResource):
    def __init__(self, *args):
        super(MapCollection, self).__init__(*args)
        self.items = None

    def on_get(self, resource):
        self.items = []
        for r in resource['resources']:
            m = Map(r['url'])
            self.items.append(m)
            m.get()
