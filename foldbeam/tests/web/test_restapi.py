import json
import urlparse

from tornado.testing import AsyncHTTPTestCase
from foldbeam.web.restapi import new_application

from .util import TempDbMixin

class BaseRestApiTestCase(AsyncHTTPTestCase, TempDbMixin):
    def get_app(self):
        # We don't want 404 or 500 log spam cluttering test output
        return new_application(log_function = lambda x: None)

    def setUp(self):
        AsyncHTTPTestCase.setUp(self)
        TempDbMixin.setUp(self)

    def tearDown(self):
        TempDbMixin.tearDown(self)
        AsyncHTTPTestCase.tearDown(self)

    def _fetch_full(self, url, *args, **kwargs):
        self.http_client.fetch(url, self.stop, *args, **kwargs)
        return self.wait()

    def _decode(self, response):
        decoded = None
        if 'Content-Type' in response.headers and response.headers['Content-Type'].split(';')[0] == 'application/json':
            decoded = json.loads(response.body)
        return response, decoded

    def get(self, path, **kwargs):
        return self._decode(self._fetch_full(urlparse.urljoin(self.get_url('/'), path), method='GET', **kwargs))

    def put(self, path, body=None, **kwargs):
        if body is not None:
            body = json.dumps(body)
        return self._decode(self._fetch_full(urlparse.urljoin(self.get_url('/'), path), method='PUT', body=body or '', **kwargs))

#    def delete(self, path, **kwargs):
#        return self._decode(self._fetch_full(urlparse.urljoin(self.get_url('/'), path), method='DELETE', **kwargs))

    def post(self, path, body=None, **kwargs):
        if body is not None:
            body = json.dumps(body)
        return self._decode(self._fetch_full(urlparse.urljoin(self.get_url('/'), path), method='POST', body=body or '', **kwargs))

    def parse_collection(self, data):
        self.assertIn('window', data)
        self.assertIn('limit', data['window'])
        self.assertIn('offset', data['window'])
        resources = data['resources']
        self.assertLessEqual(len(resources), data['window']['limit'])
        return resources

    def map_collection_path(self, username):
        response, data = self.get('/' + username)
        return data['resources']['map_collection']['url']

    def new_map(self, username, request=None):
        collection_path = self.map_collection_path(username)

        response, data = self.get(collection_path)
        self.assertEqual(response.code, 200)
        old_resources = self.parse_collection(data)

        response, data = self.post(collection_path, request)
        self.assertEqual(response.code, 201)

        self.assertIn('url', data)
        self.assertIn('Location', response.headers)
        self.assertEqual(data['url'], response.headers['Location'])
        map_url = data['url']

        response, data = self.get(map_url)
        self.assertEqual(response.code, 200)
        map_id = data['uuid']

        response, data = self.get(collection_path)
        self.assertEqual(response.code, 200)
        resources = self.parse_collection(data)
        self.assertEqual(len(resources), len(old_resources) + 1)
        self.assertEqual(resources[0]['url'], map_url)

        resource_ids = list(x['uuid'] for x in resources)
        self.assertIn(map_id, resource_ids)

        return map_url

    def layer_collection_path(self, username, map_id=None):
        if map_id is None:
            response, data = self.get('/' + username)
            self.assertEqual(response.code, 200)
            return data['resources']['layer_collection']['url']
        response, data = self.get('/' + username + '/map/_uuid/' + map_id)
        self.assertEqual(response.code, 200)
        return data['resources']['layer_collection']['url']

    def new_layer(self, username, request=None, map_id=None):
        collection_path = self.layer_collection_path(username, map_id=map_id)

        response, data = self.get(collection_path)
        self.assertEqual(response.code, 200)
        old_resources = self.parse_collection(data)

        response, data = self.post(collection_path, request)
        self.assertEqual(response.code, 201)

        self.assertIn('url', data)
        self.assertIn('Location', response.headers)
        self.assertEqual(data['url'], response.headers['Location'])
        layer_url = data['url']

        response, data = self.get(layer_url)
        self.assertEqual(response.code, 200)
        layer_id = data['uuid']

        response, data = self.get(collection_path)
        self.assertEqual(response.code, 200)
        resources = self.parse_collection(data)
        self.assertEqual(len(resources), len(old_resources) + 1)
        self.assertEqual(resources[0]['url'], layer_url)

        resource_ids = list(x['uuid'] for x in resources)
        self.assertIn(layer_id, resource_ids)

        return layer_url

class Root(BaseRestApiTestCase):
    def test_root(self):
        response, _ = self.get('')
        self.assertEqual(response.code, 404)

class User(BaseRestApiTestCase):
    def test_non_existant(self):
        response, _ = self.get('/joe_nobody')
        self.assertEqual(response.code, 404)

    def test_bad_request(self):
        response = self.fetch('/test_user', method='PUT', body='This is not JSON')
        self.assertEqual(response.code, 400)

    def test_invalid_methods(self):
        response = self.fetch('/test_user', method='POST', body='')
        self.assertEqual(response.code, 405)
        response = self.fetch('/test_user', method='DELETE')
        self.assertEqual(response.code, 405)

    def test_create_user(self):
        response, _ = self.get('/test_user_create')
        self.assertEqual(response.code, 404)

        response, data = self.put('/test_user_create', {})
        self.assertEqual(response.code, 201)

        self.assertIn('url', data)
        self.assertIn('Location', response.headers)
        self.assertEqual(data['url'], response.headers['Location'])

        response, user = self.get(data['url'])
        self.assertIn('username', user)
        self.assertEqual(user['username'], 'test_user_create')

        self.assertIn('resources', user)
        resources = user['resources']

        self.assertIn('map_collection', resources)
        self.assertIn('url', resources['map_collection'])
        self.assertIn('layer_collection', resources)
        self.assertIn('url', resources['layer_collection'])

    def test_post_idempotency(self):
        response, _ = self.get('/test_user')
        self.assertEqual(response.code, 404)

        response, _ = self.put('/test_user')
        self.assertEqual(response.code, 201)

        response, _ = self.put('/test_user')
        self.assertEqual(response.code, 201)

class MapCollection(BaseRestApiTestCase):
    def setUp(self):
        BaseRestApiTestCase.setUp(self)

        self.put('/alice')
        assert self.get('/alice')[0].code == 200
        self.put('/bob')
        assert self.get('/bob')[0].code == 200

    def test_no_such_user_collection(self):
        collection_path = '/nobody/map'
        response, _ = self.get(collection_path)
        self.assertEqual(response.code, 404)

        response, _ = self.post(collection_path)
        self.assertEqual(response.code, 404)

        # check that the URL pattern is valid though
        collection_path = '/bob/map'
        response, data = self.get(collection_path)
        self.assertEqual(response.code, 200)
        response, data = self.post(collection_path)
        self.assertEqual(response.code, 201)

    def test_empty_collection(self):
        collection_path = self.map_collection_path('alice')
        response, data = self.get(collection_path)
        self.assertEqual(response.code, 200)
        resources = self.parse_collection(data)
        self.assertEqual(len(resources), 0)

    def test_create_map(self):
        self.assertIsNotNone(self.new_map('alice'))

    def test_create_and_update_map(self):
        map_url = self.new_map('alice', { 'name': 'FooBar', })
        response, data = self.get(map_url)
        self.assertEqual(response.code, 200)
        self.assertEqual(data['name'], 'FooBar')

class Map(BaseRestApiTestCase):
    def setUp(self):
        BaseRestApiTestCase.setUp(self)

        self.put('/alice')
        assert self.get('/alice')[0].code == 200

        self.alice_map_1_url = self.new_map('alice')
        self.alice_map_1_id = self.get(self.alice_map_1_url)[1]['uuid']
        self.alice_map_2_url = self.new_map('alice', { 'name': 'Alice map 2' })
        self.alice_map_2_id = self.get(self.alice_map_2_url)[1]['uuid']

        self.put('/bob')
        assert self.get('/bob')[0].code == 200

        self.bob_map_1_url = self.new_map('bob')
        self.bob_map_1_id = self.get(self.bob_map_1_url)[1]['uuid']
        self.bob_map_2_url = self.new_map('bob', { 'name': 'Bob map 2' })
        self.bob_map_2_id = self.get(self.bob_map_2_url)[1]['uuid']
        self.bob_map_3_url = self.new_map('bob', { 'name': 'Bob map 3' })
        self.bob_map_3_id = self.get(self.bob_map_3_url)[1]['uuid']

    def test_non_existant(self):
        response, _ = self.get('/alice/map/_uuid/nosuchmap')
        self.assertEqual(response.code, 404)

        # a plausible map
        import uuid
        response, _ = self.get('/alice/map/_uuid/' + uuid.uuid4().hex)
        self.assertEqual(response.code, 404)

        # someone else's map
        response, _ = self.get('/bob/map/_uuid/' + self.bob_map_2_id)
        self.assertEqual(response.code, 200)
        response, _ = self.get('/alice/map/_uuid/' + self.bob_map_2_id)
        self.assertEqual(response.code, 404)

        # no one's map
        response, _ = self.get('/joe_nobody/map/_uuid/' + self.bob_map_2_id)
        self.assertEqual(response.code, 404)
        response, _ = self.get('/noone/map/_uuid/' + self.bob_map_2_id)
        self.assertEqual(response.code, 404)

    def test_update(self):
        response, data = self.get(self.bob_map_2_url)
        self.assertEqual(response.code, 200)
        self.assertEqual(data['name'], 'Bob map 2')

        response, _ = self.post(self.bob_map_2_url, { 'name': 'Renamed' })
        self.assertEqual(response.code, 201)

        response, data = self.get(self.bob_map_2_url)
        self.assertEqual(response.code, 200)
        self.assertEqual(data['name'], 'Renamed')

    def test_update_no_map(self):
        # check we understand URLs
        response, data = self.get('/bob/map/_uuid/' + self.bob_map_2_id)
        self.assertEqual(response.code, 200)
        self.assertEqual(data['name'], 'Bob map 2')

        response, _ = self.post('/alice/map/_uuid/' + self.bob_map_2_id, { 'name': 'Renamed' })
        self.assertEqual(response.code, 404)

        response, _ = self.post('/nobody/map/_uuid/' + self.bob_map_2_id, { 'name': 'Renamed' })
        self.assertEqual(response.code, 404)

class UserLayerCollection(BaseRestApiTestCase):
    def setUp(self):
        BaseRestApiTestCase.setUp(self)

        self.put('/alice')
        assert self.get('/alice')[0].code == 200
        self.put('/bob')
        assert self.get('/bob')[0].code == 200

    def test_no_such_user_collection(self):
        collection_path = '/nobody/layer'
        response, data = self.get(collection_path)
        self.assertEqual(response.code, 404)

        # check that the URL pattern is valid though
        collection_path = '/bob/layer'
        response, data = self.get(collection_path)
        self.assertEqual(response.code, 200)

    def test_empty_collection(self):
        collection_path = self.layer_collection_path('alice')
        response, data = self.get(collection_path)
        self.assertEqual(response.code, 200)
        resources = self.parse_collection(data)
        self.assertEqual(len(resources), 0)

    def test_create_layer(self):
        self.assertIsNotNone(self.new_layer('alice'))

    def test_create_for_non_existant_user(self):
        response, _ = self.post('noone/layer')
        self.assertEqual(response.code, 404)

        # check that our idea of URLs is correct
        response, _ = self.post('alice/layer')
        self.assertEqual(response.code, 201)

    def test_create_and_update_layer(self):
        layer_url = self.new_layer('alice', { 'name': 'FooBar', })
        response, data = self.get(layer_url)
        self.assertEqual(response.code, 200)
        self.assertEqual(data['name'], 'FooBar')

class MapLayerCollection(BaseRestApiTestCase):
    def setUp(self):
        BaseRestApiTestCase.setUp(self)

        self.put('/alice')
        assert self.get('/alice')[0].code == 200
        self.put('/bob')
        assert self.get('/bob')[0].code == 200

        self.alice_map_1_url = self.new_map('alice')
        self.alice_map_1_id = self.get(self.alice_map_1_url)[1]['uuid']
        self.alice_map_2_url = self.new_map('alice', { 'name': 'Alice map 2' })
        self.alice_map_2_id = self.get(self.alice_map_2_url)[1]['uuid']

        self.bob_map_1_url = self.new_map('bob')
        self.bob_map_1_id = self.get(self.bob_map_1_url)[1]['uuid']
        self.bob_map_2_url = self.new_map('bob', { 'name': 'Bob map 2' })
        self.bob_map_2_id = self.get(self.bob_map_2_url)[1]['uuid']
        self.bob_map_3_url = self.new_map('bob', { 'name': 'Bob map 3' })
        self.bob_map_3_id = self.get(self.bob_map_3_url)[1]['uuid']

    def test_empty_collection(self):
        collection_path = self.layer_collection_path('alice', self.alice_map_1_id)
        response, data = self.get(collection_path)
        self.assertEqual(response.code, 200)
        resources = self.parse_collection(data)
        self.assertEqual(len(resources), 0)

    def test_others_collection(self):
        collection_path = '/alice/map/_uuid/' + self.alice_map_1_id + '/layer'
        response, data = self.get(collection_path)
        self.assertEqual(response.code, 200)
        collection_path = '/bob/map/_uuid/' + self.alice_map_1_id + '/layer'
        response, data = self.get(collection_path)
        self.assertEqual(response.code, 404)
        import uuid
        collection_path = '/bob/map/_uuid/' + uuid.uuid4().hex + '/layer'
        response, data = self.get(collection_path)
        self.assertEqual(response.code, 404)

    def test_create_layer(self):
        l_url = self.new_layer('alice', map_id=self.alice_map_1_id)
        response, data = self.get(self.layer_collection_path('alice', self.alice_map_1_id))
        self.assertEqual(response.code, 200)
        resources = self.parse_collection(data)
        self.assertIn(l_url, list(x['url'] for x in resources))
        response, data = self.get(self.layer_collection_path('alice'))
        self.assertEqual(response.code, 200)
        resources = self.parse_collection(data)
        self.assertIn(l_url, list(x['url'] for x in resources))

    def test_create_layer_other(self):
        response, data = self.post('/alice/map/_uuid/' + self.alice_map_1_id + '/layer')
        self.assertEqual(response.code, 201)
        response, data = self.post('/bob/map/_uuid/' + self.alice_map_1_id + '/layer')
        self.assertEqual(response.code, 404)

    def test_create_layer_no_map(self):
        response, data = self.post('/alice/map/_uuid/' + self.alice_map_1_id + '/layer')
        self.assertEqual(response.code, 201)
        import uuid
        response, data = self.post('/alice/map/_uuid/' + uuid.uuid4().hex + '/layer')
        self.assertEqual(response.code, 404)

class Layer(BaseRestApiTestCase):
    def setUp(self):
        BaseRestApiTestCase.setUp(self)

        self.put('/alice')
        assert self.get('/alice')[0].code == 200

        self.alice_layer_1_url = self.new_layer('alice')
        self.alice_layer_1_id = self.get(self.alice_layer_1_url)[1]['uuid']
        self.alice_layer_2_url = self.new_layer('alice', { 'name': 'Alice layer 2' })
        self.alice_layer_2_id = self.get(self.alice_layer_2_url)[1]['uuid']

        self.put('/bob')
        assert self.get('/bob')[0].code == 200

        self.bob_layer_1_url = self.new_layer('bob')
        self.bob_layer_1_id = self.get(self.bob_layer_1_url)[1]['uuid']
        self.bob_layer_2_url = self.new_layer('bob', { 'name': 'Bob layer 2' })
        self.bob_layer_2_id = self.get(self.bob_layer_2_url)[1]['uuid']
        self.bob_layer_3_url = self.new_layer('bob', { 'name': 'Bob layer 3' })
        self.bob_layer_3_id = self.get(self.bob_layer_3_url)[1]['uuid']

    def test_non_existant(self):
        response, _ = self.get('/alice/layer/_uuid/nosuchlayer')
        self.assertEqual(response.code, 404)

        # a plausible layer
        import uuid
        response, _ = self.get('/alice/layer/_uuid/' + uuid.uuid4().hex)
        self.assertEqual(response.code, 404)

        # someone else's layer
        response, _ = self.get('/bob/layer/_uuid/' + self.bob_layer_2_id)
        self.assertEqual(response.code, 200)
        response, _ = self.get('/alice/layer/_uuid/' + self.bob_layer_2_id)
        self.assertEqual(response.code, 404)

        # no one's layer
        response, _ = self.get('/joe_nobody/layer/_uuid/' + self.bob_layer_2_id)
        self.assertEqual(response.code, 404)
        response, _ = self.get('/noone/layer/_uuid/' + self.bob_layer_2_id)
        self.assertEqual(response.code, 404)

