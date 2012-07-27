import unittest

from foldbeam.web import model

from .util import TempDbMixin

class BaseTestCase(unittest.TestCase, TempDbMixin):
    def setUp(self):
        unittest.TestCase.setUp(self)
        TempDbMixin.setUp(self)

    def tearDown(self):
        TempDbMixin.tearDown(self)
        unittest.TestCase.tearDown(self)

class User(BaseTestCase):
    def test_missing_user(self):
        self.assertRaises(KeyError, lambda: model.User.from_name('nonuser'))

    def test_create_user(self):
        self.assertRaises(KeyError, lambda: model.User.from_name('test_user_1'))
        self.assertFalse(model.User.exists('test_user_1'))
        u = model.User('test_user_1')
        self.assertIsNotNone(u)
        self.assertEqual(u.username, 'test_user_1')
        self.assertSequenceEqual(list(u.map_ids), [])
        self.assertSequenceEqual(list(u.maps), [])

        self.assertFalse(model.User.exists('test_user_1'))
        u.save()
        self.assertTrue(model.User.exists('test_user_1'))

        u = model.User.from_name('test_user_1')
        self.assertIsNotNone(u)
        self.assertEqual(u.username, 'test_user_1')
        self.assertSequenceEqual(list(u.map_ids), [])
        self.assertSequenceEqual(list(u.maps), [])

    def test_user_equality(self):
        u1 = model.User('test_user_1')
        u1.save()
        u2 = model.User('test_user_2')
        u2.save()
        u3 = model.User('test_user_3')
        u3.save()

        self.assertEqual(str(u1), 'test_user_1')
        self.assertEqual(unicode(u1), u'test_user_1')

        self.assertNotEqual(u1, u2)
        self.assertNotEqual(u2, u1)
        self.assertNotEqual(u1, u3)
        self.assertNotEqual(u2, u3)
        self.assertEqual(u1, u1)
        self.assertEqual(u2, u2)
        self.assertEqual(u1, model.User.from_name('test_user_1'))
        self.assertEqual(u2, model.User.from_name('test_user_2'))
        self.assertNotEqual(u2, model.User.from_name('test_user_1'))

    def test_create_maps(self):
        self.assertRaises(KeyError, lambda: model.User.from_name('test_user_2'))
        model.User('test_user_2').save()
        u = model.User.from_name('test_user_2')

        self.assertSequenceEqual(list(u.map_ids), [])
        self.assertSequenceEqual(list(u.maps), [])

        m1 = model.Map(u) 
        m2 = model.Map(u)
        m3 = model.Map(model.User('other_user'))
        self.assertTrue(m1.is_owned_by(u))
        self.assertTrue(m2.is_owned_by(u))
        self.assertFalse(m3.is_owned_by(u))
        self.assertEqual(len(list(u.maps)), 0) # Until the maps are saved, they're not in the DB
        m1.save()
        m2.save()
        m2.save()
        self.assertTrue(m1.is_owned_by(u))
        self.assertTrue(m2.is_owned_by(u))
        self.assertFalse(m3.is_owned_by(u))

        self.assertEqual(len(list(u.maps)), 2)
        u = None
        
        u = model.User.from_name('test_user_2')
        self.assertEqual(len(list(u.map_ids)), 2)

        # order is unimportant
        map_ids = list(u.map_ids)
        self.assertItemsEqual(map_ids, [m1.map_id, m2.map_id])

class Map(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.test_user = model.User('test_user')
        self.test_user.save()

    def test_user_no_maps(self):
        maps = list(self.test_user.maps)
        self.assertEqual(len(maps), 0)
        map_ids = list(self.test_user.map_ids)
        self.assertEqual(len(map_ids), 0)

    def test_missing_map(self):
        self.assertRaises(KeyError, lambda: model.Map.from_id('nomap'))

    def test_create_map(self):
        m1 = model.Map(self.test_user, name='Foo')
        self.assertGreater(len(m1.map_id), 20)
        self.assertEqual(str(m1), 'Foo')
        self.assertEqual(unicode(m1), u'Foo')
        m2 = model.Map(self.test_user)
        self.assertNotEqual(m1.map_id, m2.map_id)

        self.assertRaises(KeyError, lambda: model.Map.from_id(m1.map_id))
        m1.save()
        self.assertEqual(model.Map.from_id(m1.map_id).map_id, m1.map_id)
        self.assertNotEqual(model.Map.from_id(m1.map_id).map_id, m2.map_id)

        self.assertIsNotNone(m2.name)
        self.assertNotEqual(m2.name, m1.name)
        self.assertEqual(m1.name, 'Foo')
        self.assertEqual(model.Map.from_id(m1.map_id).name, 'Foo')

    def test_create_layers(self):
        m = model.Map(self.test_user)
        mid = m.map_id
        m.save()
        m = model.Map.from_id(mid)

        self.assertEqual(m.layer_ids, [])
        self.assertEqual(m.layers, [])

        l1 = model.Layer(self.test_user)       
        l2 = model.Layer(self.test_user)
        [m.layer_ids.append(x.layer_id) for x in (l1, l2)]
        m.save()
        self.assertRaises(KeyError, lambda: m.layers)
        l1.save()
        l2.save()
        m = None
        
        m = model.Map.from_id(mid)
        self.assertEqual(len(m.layer_ids), 2)
        self.assertEqual(m.layer_ids[0], l1.layer_id)
        self.assertEqual(m.layer_ids[1], l2.layer_id)
        self.assertEqual(m.layers[0].layer_id, l1.layer_id)
        self.assertEqual(m.layers[1].layer_id, l2.layer_id)

class Layer(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.test_user = model.User('test_user')
        self.test_user.save()

    def test_user_no_layers(self):
        layers = list(self.test_user.layers)
        self.assertEqual(len(layers), 0)
        layer_ids = list(self.test_user.layer_ids)
        self.assertEqual(len(layer_ids), 0)

    def test_missing_layer(self):
        self.assertRaises(KeyError, lambda: model.Layer.from_id('nolayer'))

    def test_create_layer(self):
        l1 = model.Layer(self.test_user, name='My layer')
        self.assertEqual(str(l1), 'My layer')
        self.assertEqual(unicode(l1), u'My layer')
        self.assertGreater(len(l1.layer_id), 20)
        l2 = model.Layer(self.test_user)
        self.assertNotEqual(l1.layer_id, l2.layer_id)

        self.assertRaises(KeyError, lambda: model.Layer.from_id(l1.layer_id))
        l1.save()
        self.assertEqual(model.Layer.from_id(l1.layer_id).layer_id, l1.layer_id)
        self.assertNotEqual(model.Layer.from_id(l1.layer_id).layer_id, l2.layer_id)

