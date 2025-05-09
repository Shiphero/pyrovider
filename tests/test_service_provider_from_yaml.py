import pathlib

from pyrovider import service_provider_from_yaml

ANSWER = "42 is the answer"


def echo(message: str) -> str:
    return message


class Salutation:
    def __init__(self, default: str):
        self._default = default

    def say_hello(self):
        return f"Hello, {self._default}"


class AnotherClass:
    def __init__(self, collaborator):
        self.collaborator = collaborator


class Factory:
    @classmethod
    def build(cls, *args, **kwargs):
        return (args, kwargs)


def test_get_built_instance(tmp_path: pathlib.Path):
    app_services_yaml = tmp_path / "app_services.yaml"
    app_services_yaml.write_text(
        """
        echo:
            instance: tests.test_service_provider_from_yaml.echo
        """
    )

    app_services = service_provider_from_yaml(str(app_services_yaml))
    echo_function = app_services.get("echo")
    assert echo_function("Hello world!") == "Hello world!"


def test_create_instance_from_class(tmp_path: pathlib.Path):
    app_services_yaml = tmp_path / "app_services.yaml"
    app_services_yaml.write_text(
        """
        entity.hello_world:
          class: tests.test_service_provider_from_yaml.Salutation
          arguments:
            - "World!"

        entity.hello_alice:
          class: tests.test_service_provider_from_yaml.Salutation
          arguments:
            - "Alice!"
        """
    )

    app_services = service_provider_from_yaml(str(app_services_yaml))

    hello_world = app_services.get("entity.hello_world")
    assert hello_world.say_hello() == "Hello, World!"

    hello_alice = app_services.get("entity.hello_alice")
    assert hello_alice.say_hello() == "Hello, Alice!"


def test_refer_to_instance(tmp_path: pathlib.Path):
    app_services_yaml = tmp_path / "app_services.yaml"
    app_services_yaml.write_text(
        """
        entity.hello_world:
          class: tests.test_service_provider_from_yaml.Salutation
          arguments:
            - "World!"

        entity.another_class:
          class: tests.test_service_provider_from_yaml.AnotherClass
          arguments:
            - '@entity.hello_world'
        """
    )

    app_services = service_provider_from_yaml(str(app_services_yaml))
    another_class = app_services.get("entity.another_class")
    assert another_class.collaborator.say_hello() == "Hello, World!"


def test_refer_to_constant(tmp_path: pathlib.Path):
    app_services_yaml = tmp_path / "app_services.yaml"
    app_services_yaml.write_text(
        """
        entity.salutation:
          class: tests.test_service_provider_from_yaml.Salutation
          arguments:
            - '^tests.test_service_provider_from_yaml.ANSWER'
        """
    )

    app_services = service_provider_from_yaml(str(app_services_yaml))
    salutation = app_services.get("entity.salutation")
    assert salutation.say_hello() == "Hello, 42 is the answer"


def test_refer_to_environment_variable(tmp_path: pathlib.Path, monkeypatch):
    monkeypatch.setenv("USER", "Alice")
    app_services_yaml = tmp_path / "app_services.yaml"
    app_services_yaml.write_text(
        """
        entity.salutation:
          class: tests.test_service_provider_from_yaml.Salutation
          named_arguments:
            default: '$USER'
        """
    )

    app_services = service_provider_from_yaml(str(app_services_yaml))
    salutation = app_services.get("entity.salutation")
    assert salutation.say_hello() == "Hello, Alice"


def test_use_factories(tmp_path: pathlib.Path):
    app_services_yaml = tmp_path / "app_services.yaml"
    app_services_yaml.write_text(
        """
        entity.factory:
          factory: tests.test_service_provider_from_yaml.Factory
        """
    )

    app_services = service_provider_from_yaml(str(app_services_yaml))
    built_object = app_services.get("entity.factory")
    assert built_object == ((), {})
