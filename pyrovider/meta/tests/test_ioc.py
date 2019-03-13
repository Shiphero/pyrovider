import unittest

from pyrovider.meta.ioc import Importer


class ImporterTest(unittest.TestCase):

    maxDiff = None

    def test_get_class(self):
        importer = Importer()
        self.assertEqual(Importer, importer.get_class('pyrovider.meta.ioc.Importer'))

    def test_get_class_undefined(self):
        importer = Importer()
        with self.assertRaises(KeyError) as context:
            importer.get_class('pyrovider.meta.ioc.Undefined')

        self.assertEqual("'Undefined'",
                         str(context.exception))
