import logging

from .base import BaseResource

class Layer(BaseResource):
    def __init__(self, *args):
        super(Layer, self).__init__(*args)
        self.name = None
        self.tiles = None

    def on_get(self, resource):
        self.name = resource['name']
        self.tiles = resource['tiles']

class LayerCollection(BaseResource):
    def __init__(self, *args):
        super(LayerCollection, self).__init__(*args)
        self.items = []

    def on_get(self, resource):
        self.items = []
        for r in resource['resources']:
            l = Layer(r['url'])
            self.items.append(l)
            l.get()
