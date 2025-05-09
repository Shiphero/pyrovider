import unittest
from pathlib import Path

import yaml

from pyrovider.services.provider import ServiceProvider

DATA_DIR = Path(__file__).parent / "data"


class NamespaceTest(unittest.TestCase):
    service_conf_path = DATA_DIR / "service_conf_with_namespaces.yaml"

    def setUp(self):
        # Given...
        self.provider = ServiceProvider()
        with open(self.service_conf_path) as fp:
            self.service_conf = yaml.safe_load(fp.read())

        self.provider.conf(self.service_conf)

    def test_getting_available_namespaces(self):
        self.assertEqual(list(self.provider.namespaces), ["foo"])
        self.assertEqual(list(self.provider.service_names), ["service1"])

        self.assertEqual(list(self.provider.foo.namespaces), ["bar"])
        self.assertEqual(list(self.provider.foo.service_names), ["service2", "service3"])

        self.assertEqual(list(self.provider.foo.bar.namespaces), [])
        self.assertEqual(list(self.provider.foo.bar.service_names), ["service4"])

    def test_getting_namespace_services(self):
        from .test_provider import MockServiceA, MockServiceI

        assert self.provider.service1
        assert isinstance(self.provider.service1, MockServiceA)

        # Access by key
        assert self.provider.get("service1")
        assert isinstance(self.provider.get("service1"), MockServiceA)

        assert self.provider.foo.service2
        assert isinstance(self.provider.foo.service2, MockServiceI)

        # Access by key
        assert self.provider.get("foo.service2")
        assert isinstance(self.provider.get("foo.service2"), MockServiceI)

        assert self.provider.foo.get("service2")
        assert isinstance(self.provider.foo.get("service2"), MockServiceI)

    def test_getting_by_dot_notation(self):
        assert self.provider.foo
        assert self.provider.foo.bar
        assert self.provider.foo.bar.service4

        assert self.provider.get("foo.bar.service4")
        assert self.provider.foo.get("bar.service4")
        assert self.provider.foo.bar.get("service4")

        # Namespaces have a path
        assert self.provider.foo.path == "foo"
        assert self.provider.foo.bar.path == "foo.bar"

    def test_setting_service_in_namespace(self):
        class Dummy:
            pass

        d = Dummy()

        self.provider.foo.bar.set("service4", d)
        assert self.provider.foo.bar.service4 == d
