# -*- coding: utf-8 -*-
from test.picardtestcase import PicardTestCase

from picard import config
from picard.metadata import (
    MULTI_VALUED_JOINER,
    Metadata,
)

settings = {
    'write_id3v23': False,
    'id3v23_join_with': '/',
}


class MetadataTest(PicardTestCase):

    original = None
    tags = []

    def setUp(self):
        super().setUp()
        config.setting = settings.copy()
        self.metadata = Metadata()
        self.metadata["single1"] = "single1-value"
        self.metadata.add_unique("single2", "single2-value")
        self.metadata.add_unique("single2", "single2-value")
        self.multi1 = ["multi1-value", "multi1-value"]
        self.metadata.add("multi1", self.multi1[0])
        self.metadata.add("multi1", self.multi1[1])
        self.multi2 = ["multi2-value1", "multi2-value2"]
        self.metadata["multi2"] = self.multi2
        self.multi3 = ["multi3-value1", "multi3-value2"]
        self.metadata.set("multi3", self.multi3)
        self.metadata["~hidden"] = "hidden-value"

    def tearDown(self):
        pass

    def test_metadata_setitem(self):
        self.assertEqual(["single1-value"], self.metadata.getraw("single1"))
        self.assertEqual(["single2-value"], self.metadata.getraw("single2"))
        self.assertEqual(self.multi1, self.metadata.getraw("multi1"))
        self.assertEqual(self.multi2, self.metadata.getraw("multi2"))
        self.assertEqual(self.multi3, self.metadata.getraw("multi3"))
        self.assertEqual(["hidden-value"], self.metadata.getraw("~hidden"))

    def test_metadata_get(self):
        self.assertEqual("single1-value", self.metadata["single1"])
        self.assertEqual("single1-value", self.metadata.get("single1"))
        self.assertEqual(["single1-value"], self.metadata.getall("single1"))
        self.assertEqual(["single1-value"], self.metadata.getraw("single1"))

        self.assertEqual(MULTI_VALUED_JOINER.join(self.multi1), self.metadata["multi1"])
        self.assertEqual(MULTI_VALUED_JOINER.join(self.multi1), self.metadata.get("multi1"))
        self.assertEqual(self.multi1, self.metadata.getall("multi1"))
        self.assertEqual(self.multi1, self.metadata.getraw("multi1"))

        self.assertEqual("", self.metadata["nonexistent"])
        self.assertEqual(None, self.metadata.get("nonexistent"))
        self.assertEqual([], self.metadata.getall("nonexistent"))
        self.assertRaises(KeyError, self.metadata.getraw, "nonexistent")

        self.assertEqual(self.metadata._store.items(), self.metadata.rawitems())
        metadata_items = [(x, z) for (x, y) in self.metadata.rawitems() for z in y]
        self.assertEqual(metadata_items, list(self.metadata.items()))

    def test_metadata_delete(self):
        self.metadata.delete("single1")
        self.assertNotIn("single1", self.metadata)
        self.assertIn("single1", self.metadata.deleted_tags)

    def test_metadata_implicit_delete(self):
        self.metadata["single2"] = ""
        self.assertNotIn("single2", self.metadata)
        self.assertIn("single2", self.metadata.deleted_tags)

        self.metadata["unknown"] = ""
        self.assertNotIn("unknown", self.metadata)
        self.assertNotIn("unknown", self.metadata.deleted_tags)

    def test_metadata_set_explicit_empty(self):
        self.metadata.delete("single1")
        self.metadata.set("single1", [])
        self.assertIn("single1", self.metadata)
        self.assertNotIn("single1", self.metadata.deleted_tags)
        self.assertEqual([], self.metadata.getall("single1"))

    def test_metadata_undelete(self):
        self.metadata.delete("single1")
        self.assertNotIn("single1", self.metadata)
        self.assertIn("single1", self.metadata.deleted_tags)

        self.metadata["single1"] = "value1"
        self.assertIn("single1", self.metadata)
        self.assertNotIn("single1", self.metadata.deleted_tags)

    def test_metadata_update(self):
        m = Metadata()
        m["old"] = "old-value"
        self.metadata.delete("single1")
        m.update(self.metadata)
        self.assertIn("old", m)
        self.assertNotIn("single1", m)
        self.assertIn("single1", m.deleted_tags)
        self.assertEqual("single2-value", m["single2"])
        self.assertEqual(self.metadata.deleted_tags, m.deleted_tags)

        self.metadata["old"] = "old-value"
        for (key, value) in self.metadata.rawitems():
            self.assertIn(key, m)
            self.assertEqual(value, m.getraw(key))
        for (key, value) in m.rawitems():
            self.assertIn(key, self.metadata)
            self.assertEqual(value, self.metadata.getraw(key))

    def test_metadata_clear(self):
        self.metadata.clear()
        self.assertEqual(0, len(self.metadata))

    def test_metadata_clear_deleted(self):
        self.metadata.delete("single1")
        self.assertIn("single1", self.metadata.deleted_tags)
        self.metadata.clear_deleted()
        self.assertNotIn("single1", self.metadata.deleted_tags)

    def test_metadata_applyfunc(self):
        def func(x): return x[1:]
        self.metadata.apply_func(func)

        self.assertEqual("ingle1-value", self.metadata["single1"])
        self.assertEqual("ingle1-value", self.metadata.get("single1"))
        self.assertEqual(["ingle1-value"], self.metadata.getall("single1"))

        self.assertEqual(MULTI_VALUED_JOINER.join(map(func, self.multi1)), self.metadata["multi1"])
        self.assertEqual(MULTI_VALUED_JOINER.join(map(func, self.multi1)), self.metadata.get("multi1"))
        self.assertEqual(list(map(func, self.multi1)), self.metadata.getall("multi1"))

    def test_length_score(self):
        results = [(20000, 0, 0.333333333333),
                   (20000, 10000, 0.666666666667),
                   (20000, 20000, 1.0),
                   (20000, 30000, 0.666666666667),
                   (20000, 40000, 0.333333333333),
                   (20000, 50000, 0.0)]
        for (a, b, expected) in results:
            actual = Metadata.length_score(a, b)
            self.assertAlmostEqual(expected, actual,
                                   msg="a={a}, b={b}".format(a=a, b=b))

    def test_compare_is_equal(self):
        m1 = Metadata()
        m1["title"] = "title1"
        m1["tracknumber"] = "2"
        m1.length = 360
        m2 = Metadata()
        m2["title"] = "title1"
        m2["tracknumber"] = "2"
        m2.length = 360
        self.assertEqual(m1.compare(m2), m2.compare(m1))
        self.assertEqual(m1.compare(m2), 1)

    def test_compare_lengths(self):
        m1 = Metadata()
        m1.length = 360
        m2 = Metadata()
        m2.length = 300
        self.assertAlmostEqual(m1.compare(m2), 0.998)

    def test_compare_tracknumber_difference(self):
        m1 = Metadata()
        m1["tracknumber"] = "1"
        m2 = Metadata()
        m2["tracknumber"] = "2"
        self.assertEqual(m1.compare(m2), 0)

    def test_compare_deleted(self):
        m1 = Metadata()
        m1["artist"] = "TheArtist"
        m1["title"] = "title1"
        m2 = Metadata()
        m2["artist"] = "TheArtist"
        m2.delete("title")
        self.assertTrue(m1.compare(m2) < 1)

    def test_metadata_mapping_init(self):
        d = {'a': 'b', 'c': 2, 'd': ['x', 'y'], 'x': ''}
        deleted_tags = set('c')
        m = Metadata(d, deleted_tags=deleted_tags, length=1234)
        self.assertTrue('a' in m)
        self.assertEqual(m.getraw('a'), ['b'])
        self.assertEqual(m['d'], MULTI_VALUED_JOINER.join(d['d']))
        self.assertNotIn('c', m)
        self.assertIn('c', m.deleted_tags)
        self.assertEqual(m.length, 1234)

    def test_metadata_mapping_del(self):
        d = {'a': 'b', 'c': 2, 'd': ['x', 'y'], 'x': ''}
        m = Metadata(d)
        self.assertEqual(m.getraw('a'), ['b'])
        self.assertNotIn('a', m.deleted_tags)
        del m['a']
        self.assertRaises(KeyError, m.getraw, 'a')
        self.assertIn('a', m.deleted_tags)

    def test_metadata_mapping_iter(self):
        d = {'a': 'b', 'c': 2, 'd': ['x', 'y'], 'x': ''}
        m = Metadata(d)
        l = set(m)
        self.assertEqual(l, {'a', 'c', 'd'})

    def test_metadata_mapping_keys(self):
        d = {'a': 'b', 'c': 2, 'd': ['x', 'y'], 'x': ''}
        m = Metadata(d)
        l = set(m.keys())
        self.assertEqual(l, {'a', 'c', 'd'})

    def test_metadata_mapping_values(self):
        d = {'a': 'b', 'c': 2, 'd': ['x', 'y'], 'x': ''}
        m = Metadata(d)
        l = set(m.values())
        self.assertEqual(l, {'b', '2', 'x; y'})

    def test_metadata_mapping_len(self):
        d = {'a': 'b', 'c': 2, 'd': ['x', 'y'], 'x': ''}
        m = Metadata(d)
        self.assertEqual(len(m), 3)
        del m['x']
        self.assertEqual(len(m), 3)
        del m['c']
        self.assertEqual(len(m), 2)
        #TODO: test with cover art images

    def test_metadata_mapping_update(self):
        d = {'a': 'b', 'c': 2, 'd': ['x', 'y'], 'x': 'z'}
        m = Metadata(d)

        d2 = {'c': 3, 'd': ['u', 'w'], 'x': ''}
        m2 = Metadata(d2)

        m.update(d2)
        self.assertEqual(m['a'], 'b')
        self.assertEqual(m['c'], '3')
        self.assertEqual(m.getraw('d'), ['u', 'w'])
        self.assertNotIn('x', m)
        self.assertIn('x', m.deleted_tags)
