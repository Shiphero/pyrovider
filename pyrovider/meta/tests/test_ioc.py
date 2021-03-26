import unittest

from pyrovider.meta.ioc import Importer

test_config = {
    "host": "localhost1",
    "host-dash": "localhost2",
    "host_underscore": "localhost2",
    "host123": "localhost3",
}


class ImporterTest(unittest.TestCase):
    maxDiff = None

    def test_get_obj(self):
        importer = Importer()
        self.assertEqual(Importer, importer.get_obj('pyrovider.meta.ioc.Importer'))

    def test_get_obj_undefined(self):
        importer = Importer()
        with self.assertRaises(KeyError) as context:
            importer.get_obj('pyrovider.meta.ioc.Undefined')

        self.assertEqual("'Undefined'",
                         str(context.exception))

    def test_get_obj_dictionary_key(self):
        importer = Importer()
        package = 'pyrovider.meta.tests.test_ioc'

        self.assertEqual(test_config["host"], importer.get_obj(f'{package}.test_config["host"]'))
        self.assertEqual(test_config["host-dash"], importer.get_obj(f'{package}.test_config["host-dash"]'))
        self.assertEqual(test_config["host_underscore"], importer.get_obj(f'{package}.test_config["host_underscore"]'))
        self.assertEqual(test_config["host123"], importer.get_obj(f'{package}.test_config["host123"]'))
