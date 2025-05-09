import unittest

from pyrovider.meta.ioc import Importer


class ImporterTest(unittest.TestCase):
    maxDiff = None

    def test_get_obj(self):
        importer = Importer()
        self.assertEqual(Importer, importer.get_obj("pyrovider.meta.ioc.Importer"))

    def test_get_obj_undefined(self):
        importer = Importer()
        with self.assertRaises(KeyError) as context:
            importer.get_obj("pyrovider.meta.ioc.Undefined")

        self.assertEqual("'Undefined'", str(context.exception))
