import json
import os
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

    def put_raw(self, path, body=None, **kwargs):
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

    def new_bucket(self, username, request=None):
        collection_path = self.bucket_collection_path(username)

        response, data = self.get(collection_path)
        self.assertEqual(response.code, 200)
        old_resources = self.parse_collection(data)

        response, data = self.post(collection_path, request)
        self.assertEqual(response.code, 201)

        self.assertIn('url', data)
        self.assertIn('uuid', data)
        reported_uuid = data['uuid']
        self.assertIn('Location', response.headers)
        self.assertEqual(data['url'], response.headers['Location'])
        bucket_url = data['url']

        response, data = self.get(bucket_url)
        self.assertEqual(response.code, 200)
        bucket_id = data['uuid']

        self.assertEqual(bucket_id, reported_uuid)

        response, data = self.get(collection_path)
        self.assertEqual(response.code, 200)
        resources = self.parse_collection(data)
        self.assertEqual(len(resources), len(old_resources) + 1)
        self.assertEqual(resources[0]['url'], bucket_url)

        resource_ids = list(x['uuid'] for x in resources)
        self.assertIn(bucket_id, resource_ids)

        return bucket_url, bucket_id

    def bucket_collection_path(self, username):
        response, data = self.get('/' + username)
        self.assertEqual(response.code, 200)
        return data['resources']['bucket_collection']['url']

class Root(BaseRestApiTestCase):
    def test_root(self):
        response, _ = self.get('')
        self.assertEqual(response.code, 404)

    def test_cors(self):
        response, _ = self.get('/joe_nobody')
        self.assertEqual(response.code, 404)
        self.assertNotIn('Access-Control-Allow-Headers', response.headers)

        response, _ = self.get('/joe_nobody', headers={'Origin': 'example.com:1234'})
        self.assertEqual(response.code, 404)

        self.assertIn('Access-Control-Allow-Headers', response.headers)
        self.assertIn('Access-Control-Allow-Origin', response.headers)
        self.assertIn('Access-Control-Allow-Methods', response.headers)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], 'example.com:1234')

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
        self.assertIn('bucket_collection', resources)
        self.assertIn('url', resources['bucket_collection'])

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

    def test_non_existant_post(self):
        body = { 'name': 'renamed_layer' }

        response, _ = self.post('/alice/layer/_uuid/nosuchlayer', body)
        self.assertEqual(response.code, 404)

        # a plausible layer
        import uuid
        response, _ = self.post('/alice/layer/_uuid/' + uuid.uuid4().hex, body)
        self.assertEqual(response.code, 404)

        # someone else's layer
        response, _ = self.post('/bob/layer/_uuid/' + self.bob_layer_2_id, body)
        self.assertEqual(response.code, 201)
        response, _ = self.post('/alice/layer/_uuid/' + self.bob_layer_2_id, body)
        self.assertEqual(response.code, 404)

        # no one's layer
        response, _ = self.post('/joe_nobody/layer/_uuid/' + self.bob_layer_2_id, body)
        self.assertEqual(response.code, 404)
        response, _ = self.post('/noone/layer/_uuid/' + self.bob_layer_2_id, body)
        self.assertEqual(response.code, 404)

    def test_rename(self):
        response, data = self.get(self.bob_layer_1_url)
        self.assertEqual(response.code, 200)
        self.assertIn('name', data)
        old_name = data['name']

        response, data = self.post(self.bob_layer_1_url, {'name': 'renamed_layer'})
        response, data = self.get(self.bob_layer_1_url)
        self.assertEqual(response.code, 200)
        self.assertIn('name', data)
        self.assertNotEqual(old_name, 'renamed_layer')
        self.assertEqual(data['name'], 'renamed_layer')

    def test_add_buckets(self):
        b1_url, b1_id = self.new_bucket('alice')
        b2_url, b2_id = self.new_bucket('alice')

        # Adding buckets from other users is fine for the moment
        response, data = self.post(self.bob_layer_1_url, {'bucket': b1_id})
        self.assertEqual(response.code, 201)

        response, data = self.get(self.bob_layer_1_url)
        self.assertEqual(response.code, 200)

        self.assertIn('bucket', data)
        self.assertEqual(data['bucket']['url'], b1_url)
        self.assertEqual(data['bucket']['uuid'], b1_id)

class BucketCollection(BaseRestApiTestCase):
    def setUp(self):
        BaseRestApiTestCase.setUp(self)

        self.put('/alice')
        assert self.get('/alice')[0].code == 200
        self.put('/bob')
        assert self.get('/bob')[0].code == 200

    def test_no_such_user_collection(self):
        collection_path = '/nobody/bucket'
        response, _ = self.get(collection_path)
        self.assertEqual(response.code, 404)

        response, _ = self.post(collection_path)
        self.assertEqual(response.code, 404)

        # check that the URL pattern is valid though
        collection_path = '/bob/bucket'
        response, data = self.get(collection_path)
        self.assertEqual(response.code, 200)
        response, data = self.post(collection_path)
        self.assertEqual(response.code, 201)

    def test_empty_collection(self):
        collection_path = self.bucket_collection_path('alice')
        response, data = self.get(collection_path)
        self.assertEqual(response.code, 200)
        resources = self.parse_collection(data)
        self.assertEqual(len(resources), 0)

    def test_create_bucket(self):
        self.assertIsNotNone(self.new_bucket('alice')[0])

    def test_create_and_update_bucket(self):
        bucket_url, bucket_id = self.new_bucket('alice', { 'name': 'FooBar', })
        response, data = self.get(bucket_url)
        self.assertEqual(response.code, 200)
        self.assertEqual(data['name'], 'FooBar')

class Bucket(BaseRestApiTestCase):
    def data_file(self, name):
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
        path = os.path.join(data_dir, name)
        return open(path)

    def setUp(self):
        BaseRestApiTestCase.setUp(self)

        self.put('/alice')
        assert self.get('/alice')[0].code == 200

        self.alice_bucket_1_url, _ = self.new_bucket('alice')
        self.alice_bucket_1_id = self.get(self.alice_bucket_1_url)[1]['uuid']
        self.alice_bucket_2_url, _ = self.new_bucket('alice', { 'name': 'Alice bucket 2' })
        self.alice_bucket_2_id = self.get(self.alice_bucket_2_url)[1]['uuid']

        self.put('/bob')
        assert self.get('/bob')[0].code == 200

        self.bob_bucket_1_url, _ = self.new_bucket('bob')
        self.bob_bucket_1_id = self.get(self.bob_bucket_1_url)[1]['uuid']
        self.bob_bucket_2_url, _ = self.new_bucket('bob', { 'name': 'Bob bucket 2' })
        self.bob_bucket_2_id = self.get(self.bob_bucket_2_url)[1]['uuid']
        self.bob_bucket_3_url, _ = self.new_bucket('bob', { 'name': 'Bob bucket 3' })
        self.bob_bucket_3_id = self.get(self.bob_bucket_3_url)[1]['uuid']

    def test_non_existant(self):
        response, _ = self.get('/alice/bucket/_uuid/nosuchbucket')
        self.assertEqual(response.code, 404)

        # a plausible bucket
        import uuid
        response, _ = self.get('/alice/bucket/_uuid/' + uuid.uuid4().hex)
        self.assertEqual(response.code, 404)

        # someone else's bucket
        response, _ = self.get('/bob/bucket/_uuid/' + self.bob_bucket_2_id)
        self.assertEqual(response.code, 200)
        response, _ = self.get('/alice/bucket/_uuid/' + self.bob_bucket_2_id)
        self.assertEqual(response.code, 404)

        # no one's bucket
        response, _ = self.get('/joe_nobody/bucket/_uuid/' + self.bob_bucket_2_id)
        self.assertEqual(response.code, 404)
        response, _ = self.get('/noone/bucket/_uuid/' + self.bob_bucket_2_id)
        self.assertEqual(response.code, 404)

    def test_non_existant_post(self):
        body = {'name': 'renamed_bucket'}

        response, _ = self.post('/alice/bucket/_uuid/nosuchbucket', body)
        self.assertEqual(response.code, 404)

        # a plausible bucket
        import uuid
        response, _ = self.post('/alice/bucket/_uuid/' + uuid.uuid4().hex, body)
        self.assertEqual(response.code, 404)

        # someone else's bucket
        response, _ = self.post('/bob/bucket/_uuid/' + self.bob_bucket_2_id, body)
        self.assertEqual(response.code, 201)
        response, _ = self.post('/alice/bucket/_uuid/' + self.bob_bucket_2_id, body)
        self.assertEqual(response.code, 404)

        # no one's bucket
        response, _ = self.post('/joe_nobody/bucket/_uuid/' + self.bob_bucket_2_id, body)
        self.assertEqual(response.code, 404)
        response, _ = self.post('/noone/bucket/_uuid/' + self.bob_bucket_2_id, body)
        self.assertEqual(response.code, 404)

    def test_bad_urls(self):
        # check that our idea of URLs is right
        response, _ = self.put_raw('/bob/bucket/_uuid/' + self.bob_bucket_2_id + '/foo',
                self.data_file('spain.tiff').read())
        self.assertEqual(response.code, 201)

        # someone else's bucket
        response, _ = self.put_raw('/alice/bucket/_uuid/' + self.bob_bucket_2_id + '/foo',
                self.data_file('spain.tiff').read())
        self.assertEqual(response.code, 404)

        # non-existant bucket
        import uuid
        response, _ = self.put_raw('/alice/bucket/_uuid/' + uuid.uuid4().hex + '/foo',
                self.data_file('spain.tiff').read())
        self.assertEqual(response.code, 404)

        # someone who doesn't exist's bucket
        response, _ = self.put_raw('/joe_nobody/bucket/_uuid/' + self.bob_bucket_2_id + '/foo',
                self.data_file('spain.tiff').read())
        self.assertEqual(response.code, 404)

    def test_bad_filenames(self):
        # check bucket exists
        response, data = self.get(self.bob_bucket_1_url)
        self.assertEqual(response.code, 200)

        # try to break out
        response, _ = self.put_raw(self.bob_bucket_1_url + '/../foo.shp', self.data_file('ne_110m_admin_0_countries.shp').read())
        self.assertEqual(response.code, 404)

        # encode slash
        response, _ = self.put_raw(self.bob_bucket_1_url + '/..%2Ffoo.shp', self.data_file('ne_110m_admin_0_countries.shp').read())
        self.assertEqual(response.code, 400) # filenames with slashes in are bad m'kay?

        # encode try to break out of bucket
        response, _ = self.put_raw(self.bob_bucket_1_url + '/..', self.data_file('ne_110m_admin_0_countries.shp').read())
        self.assertEqual(response.code, 400) # filenames with slashes in are bad m'kay?

    def test_empty_bucket(self):
        response, data = self.get(self.bob_bucket_1_url)
        self.assertEqual(response.code, 200)

        self.assertIn('layers', data)
        self.assertItemsEqual(data['layers'], [])

        self.assertIn('files', data)
        self.assertItemsEqual(data['files'], [])

    def test_rename(self):
        response, data = self.get(self.bob_bucket_1_url)
        self.assertEqual(response.code, 200)
        self.assertIn('name', data)
        old_name = data['name']

        response, data = self.post(self.bob_bucket_1_url, {'name': 'renamed_bucket'})
        response, data = self.get(self.bob_bucket_1_url)
        self.assertEqual(response.code, 200)
        self.assertIn('name', data)
        self.assertNotEqual(old_name, 'renamed_bucket')
        self.assertEqual(data['name'], 'renamed_bucket')

    def test_shapefile_upload(self):
        # check bucket exists
        response, data = self.get(self.bob_bucket_1_url)
        self.assertEqual(response.code, 200)

        # upload shape file
        response, _ = self.put_raw(self.bob_bucket_1_url + '/foo.shp', self.data_file('ne_110m_admin_0_countries.shp').read())
        self.assertEqual(response.code, 201)
        response, data = self.get(self.bob_bucket_1_url)
        self.assertEqual(response.code, 200)
        self.assertIn('layers', data)
        self.assertItemsEqual(data['layers'], [])
        self.assertIn('files', data)
        self.assertItemsEqual(data['files'], ['foo.shp'])

        # upload shape index file
        response, _ = self.put_raw(self.bob_bucket_1_url + '/foo.shx', self.data_file('ne_110m_admin_0_countries.shx').read())
        self.assertEqual(response.code, 201)
        response, data = self.get(self.bob_bucket_1_url)
        self.assertEqual(response.code, 200)
        self.assertIn('layers', data)
        self.assertItemsEqual(data['files'], ['foo.shp', 'foo.shx'])
        self.assertItemsEqual(data['layers'], ['foo'])

        # check layer is vector but has no projection
        l = data['layers']['foo']
        self.assertIn('type', l)
        self.assertEqual(l['type'], 'vector')
        self.assertIn('spatial_reference', l)
        self.assertEqual(l['spatial_reference'], None)

        # upload shape projection file
        response, _ = self.put_raw(self.bob_bucket_1_url + '/foo.prj', self.data_file('ne_110m_admin_0_countries.prj').read())
        self.assertEqual(response.code, 201)
        response, data = self.get(self.bob_bucket_1_url)
        self.assertEqual(response.code, 200)
        self.assertIn('layers', data)
        self.assertItemsEqual(data['files'], ['foo.shp', 'foo.prj', 'foo.shx'])
        self.assertItemsEqual(data['layers'], ['foo'])

        # check layer is vector and has projection
        l = data['layers']['foo']
        self.assertIn('type', l)
        self.assertEqual(l['type'], 'vector')
        self.assertIn('spatial_reference', l)

        srs = l['spatial_reference']
        self.assertIn('proj', srs)
        self.assertIn('wkt', srs)
        self.assertEqual(srs['proj'], u'+proj=longlat +datum=WGS84 +no_defs ')
        self.assertEqual(srs['wkt'],
                u'GEOGCS["GCS_WGS_1984",DATUM["WGS_1984",SPHEROID["WGS_84",6378137.0,298.257223563]],' + 
                u'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]')

    def test_geotiff_upload(self):
        # check bucket exists
        response, data = self.get(self.bob_bucket_1_url)
        self.assertEqual(response.code, 200)

        # upload tiff file
        response, _ = self.put_raw(self.bob_bucket_1_url + '/image.tiff', self.data_file('spain.tiff').read())
        self.assertEqual(response.code, 201)
        response, data = self.get(self.bob_bucket_1_url)
        self.assertEqual(response.code, 200)
        self.assertIn('layers', data)
        self.assertItemsEqual(data['layers'], ['image.tiff'])
        self.assertIn('files', data)
        self.assertItemsEqual(data['files'], ['image.tiff'])

        # check layer is raster and has projection
        l = data['layers']['image.tiff']
        self.assertIn('type', l)
        self.assertEqual(l['type'], 'raster')
        self.assertIn('spatial_reference', l)

        srs = l['spatial_reference']
        self.assertIn('proj', srs)
        self.assertIn('wkt', srs)
        self.assertEqual(srs['proj'], u'+proj=utm +zone=30 +datum=WGS84 +units=m +no_defs ')
        self.assertEqual(srs['wkt'],
            u'PROJCS["WGS 84 / UTM zone 30N",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",' +
            u'6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],' +
            u'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]],' +
            u'PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",-3],' +
            u'PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],' +
            u'UNIT["metre",1,AUTHORITY["EPSG","9001"]],AUTHORITY["EPSG","32630"]]')
