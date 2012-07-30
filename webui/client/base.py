import logging

from pyjamas.EventController import EventGenerator
from pyjamas.JSONService import loads, dumps
from pyjamas.HTTPRequest import HTTPRequest

class BaseHandler(object):
    def __init__(self, cb):
        self._cb = cb

    def onCompletion(self, response):
        self._cb(200, loads(response) or response)

    def onError(self, response, status):
        self._cb(status, loads(response) or response)

class BaseResource(EventGenerator):
    def __init__(self, resource_url=None):
        self.addListenedEvent('Error')
        self.addListenedEvent('Loaded')
        self.addListenedEvent('Created')
        self.addListenedEvent('Deleted')

        self.set_resource_url(resource_url)

    def set_resource_url(self, url):
        self._resource_url = url
        return self

    def get_resource_url(self):
        return self._resource_url

    def get(self):
        HTTPRequest().asyncGet(self._resource_url, BaseHandler(self._get_cb))
        return self

    def put(self, data):
        HTTPRequest().asyncPut(self._resource_url, dumps(data or '{}'), BaseHandler(self._put_cb))
        return self

    def post(self, data):
        HTTPRequest().asyncPost(self._resource_url, dumps(data or '{}'), BaseHandler(self._post_cb))
        return self

    def delete(self):
        HTTPRequest().asyncGet(self._resource_url, BaseHandler(self._delete_cb))
        return self

    def on_error(self, method, status, response):
        logging.error('%s error using method %s on %s (%s)' % (status, method, self._resource_url, response))

    def on_get(self, response):
        pass

    def _get_cb(self, status, response):
        if status == 200:
            self.on_get(response)
            self.dispatchLoadedEvent(self)
        else:
            self.on_error('GET', status, response)
            self.dispatchErrorEvent(self, status, response)

    def on_put(self, response):
        pass

    def _put_cb(self, status, response):
        if status == 201:
            self.on_put(response)
            self.dispatchCreatedEvent(self)
        else:
            self.on_error('PUT', status, response)
            self.dispatchErrorEvent(self, status, response)

    def on_post(self, response):
        pass

    def _post_cb(self, status, response):
        if status == 201:
            self.on_post(response)
            self.dispatchCreatedEvent(self)
        else:
            self.on_error('POST', status, response)
            self.dispatchErrorEvent(self, status, response)

    def on_delete(self, response):
        pass

    def _delete_cb(self, status, response):
        if status == 200: # FIXME: chose appropriate status code
            self.on_delete(response)
            self.dispatchLoadedEvent(self)
        else:
            self.on_error('DELETE', status, response)
            self.dispatchErrorEvent(self, status, response)
