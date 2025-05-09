import pathlib
import unittest

from pyrovider.services import factories

DATA_DIR = pathlib.Path(__file__).parent / "data"


class FactoryTest(unittest.TestCase):
    def test_build_from_one_source(self):
        p = factories.service_provider_from_sources(
            factories.ServiceDefinitionSource("test", DATA_DIR / "service_conf_2.yaml")
        )

        # Services are stored in the test namespace
        assert list(p.service_names) == []
        assert list(p.namespaces) == ["test"]
        assert list(p.test.service_names) == ["serviceA", "serviceB"]

        p = factories.service_provider_from_sources(
            factories.ServiceDefinitionSource(
                "test",
                DATA_DIR / "service_conf_2.yaml",
                False,
            ),
        )

        # Services should be stored at the root level (using is_root flag when building)
        assert list(p.service_names) == ["serviceA", "serviceB"]
        assert list(p.namespaces) == []

    def test_build_from_multiple_sources(self):
        p = factories.service_provider_from_sources(
            factories.ServiceDefinitionSource("test", DATA_DIR / "service_conf_2.yaml"),
            factories.ServiceDefinitionSource(
                "test2",
                DATA_DIR / "service_conf_with_namespaces.yaml",
            ),
        )

        # Services are stored in its own namespace
        assert list(p.service_names) == []
        assert sorted(["test", "test2"]) == list(p.namespaces)
        assert list(p.test.service_names) == ["serviceA", "serviceB"]
        assert list(p.test2.service_names) == ["service1"]

        p = factories.service_provider_from_sources(
            factories.ServiceDefinitionSource(
                "test",
                DATA_DIR / "service_conf_2.yaml",
                False,
            ),
            factories.ServiceDefinitionSource(
                "test2",
                DATA_DIR / "service_conf_with_namespaces.yaml",
            ),
        )

        # Services should be stored at the root level (using is_root flag when building)
        assert list(p.service_names) == ["serviceA", "serviceB"]
        assert list(p.namespaces) == ["test2"]
        assert list(p.test2.service_names) == ["service1"]
        assert list(p.test2.namespaces) == ["foo"]

    def test_build_with_parent(self):
        parent = factories.service_provider_from_yaml(DATA_DIR / "service_conf_2.yaml")

        # Give it a name (the yaml doesn't have one)
        parent.name = "parent"

        p = factories.service_provider_from_yaml(
            DATA_DIR / "service_conf_with_namespaces.yaml",
            parent,
        )

        assert sorted(["foo", "parent"]) == sorted(p.namespaces)
        assert list(p.service_names) == ["service1"]

        assert list(p.parent.service_names) == ["serviceA", "serviceB"]
        assert list(p.parent.namespaces) == []

        assert p.get("parent.serviceA")
        assert p.parent.get("serviceA")
