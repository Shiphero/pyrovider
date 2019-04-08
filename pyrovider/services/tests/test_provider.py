import unittest

import mock
import yaml
from pyrovider.services.provider import (BadConfPathError,
                                         NoCreationMethodError,
                                         NotAServiceFactoryError,
                                         ServiceFactory, ServiceProvider,
                                         TooManyCreationMethodsError,
                                         UnknownServiceError)


class ModelSchemataTest(unittest.TestCase):

    maxDiff = None
    service_conf_path = 'pyrovider/services/tests/test_provider/service_conf.yaml'
    app_conf_path = 'pyrovider/services/tests/test_provider/app_conf.yaml'

    def setUp(self):
        # Given...
        self.provider = ServiceProvider()
        with open(self._local.service_conf_path, 'r') as fp:
            self._local.service_conf = yaml.load(fp.read())
        with open(self._local.app_conf_path, 'r') as fp:
            self._local.app_conf = yaml.load(fp.read())
        self.provider.conf(self._local.service_conf, self._local.app_conf)

    def test_getting_an_instance_service(self):
        # When...
        service_h = self.provider.get('service-h')
        # Then...
        self.assertEquals(service_h, mock_service_instance)

    def test_getting_a_service_with_a_service_dependency(self):
        # When...
        service_b = self.provider.get('service-b')
        # Then...
        self.assertIsInstance(service_b.service_a, MockServiceA)

    def test_getting_a_service_with_a_service_named_dependency(self):
        # When...
        password = 'qwerty'
        service_b = self.provider.get('service-b', password=password)
        # Then...
        self.assertEqual(service_b.password, password)

    def test_getting_a_service_with_a_config_dependency(self):
        # When...
        service_b = self.provider.get('service-b')
        # Then...
        self.assertEqual({'version': '1',
                          'url': "https://api.some-app.com/v1/"},
                         service_b.some_configuration)

    def test_getting_a_service_with_an_env_var_dependency(self):
        # When...
        import os
        os.environ['SOME_ENV_VAR'] = 'Not the default value.'
        service_b = self.provider.get('service-b')
        del os.environ['SOME_ENV_VAR']
        # Then...
        self.assertEqual('Not the default value.', service_b.some_env_var)

    def test_getting_a_service_with_an_env_var_dependency_with_a_literal_default(self):
        # When...
        service_b = self.provider.get('service-b')
        # Then...
        self.assertEqual('Some default value.', service_b.some_env_var)

    def test_getting_a_service_with_an_env_var_dependency_with_a_config_default(self):
        # When...
        service_b = self.provider.get('service-b')
        # Then...
        self.assertEqual("https://api.some-app.com/v1/", service_b.other_env_var)

    def test_getting_a_service_with_a_list_of_references_dependency(self):
        # When...
        service_i = self.provider.get('service-i')
        # Then...
        self.assertIsInstance(service_i.some_services_1[0], MockServiceA)
        self.assertIsInstance(service_i.some_services_1[1], MockServiceB)
        self.assertIsInstance(service_i.some_services_2[0], MockServiceC)
        self.assertIs(service_i.some_services_2[1], mock_service_instance)

    def test_getting_a_service_with_a_literal_dependency(self):
        # When...
        service_b = self.provider.get('service-b')
        # Then...
        self.assertEqual('A literal value.', service_b.some_literal_value)

    def test_getting_a_service_with_a_factory(self):
        # When...
        service_c = self.provider.get('service-c')
        # Then...
        self.assertIsInstance(service_c.service_b, MockServiceB)

    def test_getting_a_service_with_a_factory_named_dependency(self):
        # When...
        service_a = object()
        service_c = self.provider.get('service-c', service_a=service_a)
        # Then...
        self.assertEqual(service_c.service_a, service_a)

    def test_getting_unknown_service(self):
        with self.assertRaises(UnknownServiceError) as context:
            self.provider.get('service-unknown')
        self.assertEqual('"service-unknown" is not a service we know of.',
                         str(context.exception))

    def test_getting_no_creation_methods(self):
        with self.assertRaises(NoCreationMethodError) as context:
            self.provider.get('service-d')
        self.assertEqual('You must define either a class, an instance, or a factory '
                         'for the service "service-d", none was found.',
                         str(context.exception))

    def test_getting_too_many_creation_methods(self):
        with self.assertRaises(TooManyCreationMethodsError) as context:
            self.provider.get('service-e')
        self.assertEqual('You must define either a class, an instance, or a factory '
                         'for the service "service-e", not both.',
                         str(context.exception))

    def test_getting_not_a_service_factory(self):
        with self.assertRaises(NotAServiceFactoryError) as context:
            self.provider.get('service-f')
        self.assertEqual('The factory class for the service "service-f" '
                         'does not have a "build" method.',
                         str(context.exception))

    def test_getting_a_service_with_broken_dependencies(self):
        # When...
        self.provider = ServiceProvider()
        self.provider.conf(self._local.service_conf)
        with self.assertRaises(BadConfPathError) as context:
            self.provider.get('service-b')
        # Then...
        self.assertEqual('The path "some_app" was not found in the app configuration.',
                         str(context.exception))

    def test_getting_service_factory_without_build(self):
        # When, then...
        with self.assertRaises(NotImplementedError):
            self.provider.get('service-g')

    def test_setting_known_service(self):
        # Given...
        service = mock.MagicMock()
        service.do = mock.MagicMock(return_value="Yeah")
        # When...
        self.provider.set('service-a', service)
        service = self.provider.get('service-a')
        # Then...
        self.assertIsInstance(service, mock.MagicMock)
        self.assertEquals("Yeah", service.do())

    def test_setting_unknown_service(self):
        # Given...
        service = mock.MagicMock()
        # When, then...
        with self.assertRaises(UnknownServiceError):
            self.provider.set('service-z', service)


class MockServiceA():

    pass


class MockServiceB():

    def __init__(self,
                 service_a,
                 some_configuration,
                 some_env_var,
                 other_env_var,
                 some_literal_value,
                 password):
        self.service_a = service_a
        self.some_configuration = some_configuration
        self.some_env_var = some_env_var
        self.other_env_var = other_env_var
        self.some_literal_value = some_literal_value
        self.password = password


class MockServiceC():

    def __init__(self):
        self.service_a = None
        self.service_b = None


class MockServiceI():

    def __init__(self,
                 some_services_1,
                 some_services_2):
        self.some_services_1 = some_services_1
        self.some_services_2 = some_services_2


class MockServiceFactory(ServiceFactory):

    def __init__(self, service_b, service_a=None):
        self.service_a = service_a
        self.service_b = service_b

    def build(self):
        service_c = MockServiceC()
        service_c.service_a = self.service_a
        service_c.service_b = self.service_b

        return service_c


class MockServiceFactoryWithoutBuild(ServiceFactory):

    pass


def mock_service_instance():
    pass


if __name__ == '__main__':
    unittest.main()
