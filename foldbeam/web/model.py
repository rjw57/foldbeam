import itertools
import os
import uuid

from shove import Shove

_data_dir = os.path.dirname(__file__)
_shelve_loc = os.path.join(_data_dir, 'db')

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

    def is_owned_by(self, user):
        return self.owner_username == user.username

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

    def __init__(self, owner, name=None):
        self.layer_id = uuid.uuid4().hex
        self.owner_username = owner.username
        self.name = name or 'Untitled layer'

    def is_owned_by(self, user):
        return self.owner_username == user.username

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
