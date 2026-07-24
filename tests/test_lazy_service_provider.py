import json
import pathlib

from pyrovider import service_provider_from_directory, split_service_definitions
from pyrovider.services.factories import LazyServiceConfig

from .test_service_provider_from_yaml import AnotherClass, Salutation


def _write_service_config(path: pathlib.Path):
    path.write_text(
        """
        __name__: lazy-provider
        entity.hello_world:
          class: tests.test_service_provider_from_yaml.Salutation
          arguments:
            - World!
        entity.another_class:
          class: tests.test_service_provider_from_yaml.AnotherClass
          arguments:
            - '@entity.hello_world'
        """
    )


def test_split_service_definitions_and_load_each_service_on_first_use(tmp_path):
    source = tmp_path / "services.yaml"
    output = tmp_path / "services.d"
    _write_service_config(source)

    split_service_definitions(source, output)
    config = LazyServiceConfig(output)

    assert config.provider_name == "lazy-provider"
    assert set(config.keys()) == {"__name__", "entity.hello_world", "entity.another_class"}
    assert config._definitions == {}
    assert config["entity.hello_world"]["class"].endswith("Salutation")
    assert set(config._definitions) == {"entity.hello_world"}


def test_lazy_provider_preserves_references_and_namespaces(tmp_path):
    source = tmp_path / "services.yaml"
    output = tmp_path / "services.d"
    _write_service_config(source)
    split_service_definitions(source, output)

    provider = service_provider_from_directory(output)
    service = provider.get("entity.another_class")

    assert provider.name == "lazy-provider"
    assert isinstance(service, AnotherClass)
    assert isinstance(service.collaborator, Salutation)
    assert service.collaborator.say_hello() == "Hello, World!"


def test_split_uses_hash_for_unsafe_service_names(tmp_path):
    source = tmp_path / "services.yaml"
    output = tmp_path / "services.d"
    source.write_text('"unsafe/service":\n  instance: tests.test_service_provider_from_yaml.echo\n')

    manifest_path = split_service_definitions(source, output)
    manifest = json.loads(manifest_path.read_text())
    filename = manifest["services"]["unsafe/service"]

    assert "/" not in filename
    assert len(filename) == 69
    assert (output / filename).exists()
