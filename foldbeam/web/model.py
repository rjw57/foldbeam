import itertools
import os
import tempfile
import uuid

from shove import Shove

from foldbeam import bucket

_data_dir = os.path.dirname(__file__)
_shelve_loc = os.path.join(_data_dir, 'db')
_bucket_loc = os.path.join(_data_dir, 'db_bucket_storage')

class _ShoveWrapper(object):
    def __init__(self, loc):
        self._loc = loc
        self._shove = Shove(self._loc)

    def __enter__(self):
        return self._shove

    def __exit__(self, type, value, traceback):
        self._shove.close()

def _users():
    return _ShoveWrapper('file://' + _shelve_loc + '_users')

def _maps():
    return _ShoveWrapper('file://' + _shelve_loc + '_maps')

def _layers():
    return _ShoveWrapper('file://' + _shelve_loc + '_layers')

def _buckets():
    return _ShoveWrapper('file://' + _shelve_loc + '_buckets')

class User(object):
    @classmethod
    def exists(cls, username):
        with _users() as users:
            return username in users

    @classmethod
    def from_name(cls, username):
        with _users() as users:
            return users[username]

    def __init__(self, username):
        self.username = username

    @property
    def maps(self):
        return itertools.ifilter(lambda m: m.is_owned_by(self), _maps()._shove.itervalues())

    @property
    def map_ids(self):
        return itertools.imap(lambda m: m.map_id, self.maps)

    @property
    def layers(self):
        return itertools.ifilter(lambda l: l.is_owned_by(self), _layers()._shove.itervalues())

    @property
    def layer_ids(self):
        return itertools.imap(lambda l: l.layer_id, self.layers)

    @property
    def buckets(self):
        return itertools.ifilter(lambda l: l.is_owned_by(self), _buckets()._shove.itervalues())

    @property
    def bucket_ids(self):
        return itertools.imap(lambda l: l.bucket_id, self.buckets)

    def save(self):
        with _users() as users:
            users[self.username] = self

    def __eq__(self, other):
        return self.username == other.username

    def __ne__(self, other):
        return self.username != other.username

    def __str__(self):
        return str(self.username)

    def __unicode__(self):
        return unicode(self.username)

class Map(object):
    @classmethod
    def from_id(cls, map_id):
        with _maps() as maps:
            return maps[map_id]

    def __init__(self, owner, name=None, layer_ids=None):
        self.map_id = uuid.uuid4().hex
        self.owner_username = owner.username
        self.name = name or 'Untitled map'
        self.layer_ids = layer_ids or []
        self.srs = '+proj=merc +lon_0=0 +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs'
        self.extent = (-20037508.3428, -15496570.7397, 20037508.3428, 18764656.2314)

    def is_owned_by(self, user):
        return self.owner_username == user.username

    def add_layer(self, b):
        if b.layer_id not in self.layer_ids:
            self.layer_ids.append(b.layer_id)

    def remove_layer(self, b):
        if b.layer_id in self.layer_ids:
            self.layer_ids.remove(b.layer_id)

    def move_layer(self, b, index):
        """Move the layer `b` so that it now has the index `index`."""
        if b.layer_id not in self.layer_ids:
            raise KeyError

        self.layer_ids.remove(b.layer_id)
        self.layer_ids.insert(index, b.layer_id)

    @property
    def owner(self):
        return User.from_name(self.owner_username)

    @property
    def layers(self):
        return [Layer.from_id(i) for i in self.layer_ids]

    def save(self):
        with _maps() as maps:
           maps[self.map_id] = self

    def __str__(self):
        return str(self.name)

    def __unicode__(self):
        return unicode(self.name)

class Layer(object):
    @classmethod
    def from_id(cls, layer_id):
        with _layers() as layers:
           return layers[layer_id]

    def __init__(self, owner, name=None, bucket_ids=None):
        self.layer_id = uuid.uuid4().hex
        self.owner_username = owner.username
        self.name = name or 'Untitled layer'
        self.bucket_id = None
        self.bucket_layer_name = None

    def is_owned_by(self, user):
        return self.owner_username == user.username

    @property
    def source(self):
        if self.bucket_layer_name is None:
            return None

        b = self.bucket
        if b is None:
            return None

        l = list(l for l in b.bucket.layers if l.name == self.bucket_layer_name)
        if len(l) == 0:
            return None

        return l[0]

    @property
    def bucket(self):
        if self.bucket_id is None:
            return None
        return Bucket.from_id(self.bucket_id)

    @bucket.setter
    def bucket(self, b):
        if b is None:
            self.bucket_id = None
        else:
            self.bucket_id = b.bucket_id

    @property
    def owner(self):
        return User.from_name(self.owner_username)

    def save(self):
        with _layers() as layers:
            layers[self.layer_id] = self

    def __str__(self):
        return str(self.name)

    def __unicode__(self):
        return unicode(self.name)

class Bucket(object):
    @classmethod
    def from_id(cls, bucket_id):
        with _buckets() as buckets:
           return buckets[bucket_id]

    def __init__(self, owner, name=None):
        self.bucket_id = uuid.uuid4().hex
        self.owner_username = owner.username
        self.name = name or 'Untitled bucket'

        if not os.path.exists(_bucket_loc):
            os.makedirs(_bucket_loc)
        self.bucket_storage_dir = tempfile.mkdtemp(prefix='bucket_', dir=_bucket_loc)

    def is_owned_by(self, user):
        return self.owner_username == user.username

    @property
    def bucket(self):
        return bucket.Bucket(self.bucket_storage_dir)

    @property
    def owner(self):
        return User.from_name(self.owner_username)

    def save(self):
        with _buckets() as buckets:
            buckets[self.bucket_id] = self

    def __str__(self):
        return str(self.name)

    def __unicode__(self):
        return unicode(self.name)
