import hashlib
import json
import re
import typing
from collections.abc import Iterator, Mapping
from pathlib import Path
from threading import Lock

from ruamel.yaml import YAML  # type: ignore[import-untyped]

from .provider import ServiceProvider

MANIFEST_FILENAME = "manifest.json"
MANIFEST_FORMAT_VERSION = 1
_SAFE_SERVICE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
_MAX_SERVICE_FILENAME_LENGTH = 120


class LazyServiceConfig(Mapping):
    """Read service definitions from individual YAML files on first access."""

    def __init__(self, directory: typing.Union[str, Path]):
        self.directory = Path(directory)
        with (self.directory / MANIFEST_FILENAME).open() as fp:
            manifest = json.load(fp)
        if manifest.get("format") != MANIFEST_FORMAT_VERSION:
            raise ValueError("Unsupported lazy service manifest format")
        self.provider_name = manifest.get("provider_name")
        self._service_files = manifest["services"]
        self._definitions: typing.Dict[str, typing.Any] = {}
        self._lock = Lock()
        self._yaml = YAML(typ="safe")

    def __getitem__(self, name):
        if name == "__name__" and self.provider_name is not None:
            return self.provider_name
        if name not in self._service_files:
            raise KeyError(name)
        if name not in self._definitions:
            with self._lock:
                if name not in self._definitions:
                    with (self.directory / self._service_files[name]).open() as fp:
                        self._definitions[name] = self._yaml.load(fp)
        return self._definitions[name]

    def __iter__(self) -> Iterator[str]:
        if self.provider_name is not None:
            yield "__name__"
        yield from self._service_files

    def __len__(self):
        return len(self._service_files) + (self.provider_name is not None)


def service_provider_from_directory(
    service_conf_directory: typing.Union[str, Path],
    *providers,
    app_conf_path: typing.Union[str, Path, None] = None,
    name: typing.Optional[str] = None,
) -> ServiceProvider:
    """Build a provider whose service definitions load lazily from a directory."""

    provider = ServiceProvider(*providers, name=name)
    service_conf = LazyServiceConfig(service_conf_directory)
    app_conf = _load_yaml(app_conf_path) if app_conf_path is not None else None
    provider.conf(service_conf, app_conf)
    return provider


def split_service_definitions(
    service_conf_path: typing.Union[str, Path], output_directory: typing.Union[str, Path]
) -> Path:
    """Split one provider YAML into a manifest and one YAML file per service."""

    service_conf = _load_yaml(service_conf_path)
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    yaml = YAML(typ="safe")
    services = {}
    for service_name, definition in service_conf.items():
        if service_name == "__name__":
            continue
        filename = _service_definition_filename(service_name)
        with (output_path / filename).open("w") as fp:
            yaml.dump(definition, fp)
        services[service_name] = filename
    manifest = {
        "format": MANIFEST_FORMAT_VERSION,
        "provider_name": service_conf.get("__name__"),
        "services": services,
    }
    manifest_path = output_path / MANIFEST_FILENAME
    with manifest_path.open("w") as fp:
        json.dump(manifest, fp, indent=2, sort_keys=True)
        fp.write("\n")
    return manifest_path


def _service_definition_filename(service_name: str) -> str:
    filename = f"{service_name}.yaml"
    if _SAFE_SERVICE_NAME.fullmatch(service_name) and len(filename) <= _MAX_SERVICE_FILENAME_LENGTH:
        return filename
    return f"{hashlib.sha256(service_name.encode()).hexdigest()}.yaml"


def _load_yaml(path: typing.Union[str, Path]):
    yaml = YAML(typ="safe")
    with open(path) as fp:
        return yaml.load(fp)


def service_provider_from_yaml(
    service_conf_path: typing.Union[str, Path],
    *providers,
    app_conf_path: typing.Union[str, Path, None] = None,
    name: typing.Optional[str] = None,
) -> ServiceProvider:
    """Factory method for creating and configuring a ServiceProvider from YAML files.

    This function initializes a `ServiceProvider` instance with any provided
    base providers. It then loads service-specific configurations from a
    YAML file specified by `service_conf_path`. Optionally, it can also
    load application-level configurations from another YAML file specified
    by `app_conf_path`. Both configurations are then applied to the
    `ServiceProvider` instance.

    Args:
        service_conf_path: The file system path to the primary YAML
            configuration file for the service.
        *providers: Variable length argument list of Service Provider instances
        app_conf_path: An optional file path to an additional YAML
            configuration file, typically for application-level settings.
            If None, no application configuration is loaded.
        name: Optional name of the Service Provider.

    Returns:
        A `ServiceProvider` instance, configured with the settings from
        the provided YAML files.

    Raises:
        FileNotFoundError: If `service_conf_path` or `app_conf_path`
            (if provided) does not exist.
        yaml.YAMLError: If there is an error parsing the YAML content from
            the configuration files.
    """
    provider = ServiceProvider(*providers, name=name)
    service_conf = _load_yaml(service_conf_path)

    app_conf = _load_yaml(app_conf_path) if app_conf_path is not None else None

    provider.conf(service_conf, app_conf)

    return provider


class ServiceDefinitionSource:
    def __init__(self, name, path, as_namespace=True):
        self.name = name
        self.path = path
        self.as_namespace = as_namespace


def service_provider_from_sources(*sources: ServiceDefinitionSource, create_alt_names_for_dashes=True):
    """
    Builds a service provider from multiple sources

    Parameters
      sources: A list of ServiceDefinitionSource

      create_alt_names_for_dashes: For every entry with dashes in its name
                  we will create a new one with underscores os if needed it
                  can be accessed as a namespace attribute

    """
    provider = ServiceProvider()

    merged_conf = {}
    errors = []
    yaml = YAML(typ="safe")

    for source in sources:
        if not isinstance(source, ServiceDefinitionSource):
            raise TypeError(f"source must be a {ServiceDefinitionSource.__name__} instance")

        with open(source.path) as fp:
            service_conf = yaml.load(fp)

            for key, value in service_conf.items():
                service_key = f"{source.name}.{key}" if source.as_namespace else key
                alt_service_key = None

                # If there was an entry name with dashes
                # we create an alternate name with dashboards so
                # it's a valid python attribute name and can be accessed
                # with dot notation
                if create_alt_names_for_dashes and "-" in service_key:
                    alt_service_key = service_key.replace("-", "_")

                if service_key in merged_conf or alt_service_key in merged_conf:
                    errors.append(f"Duplicated entry {key} from source ({source.path})")

                merged_conf[service_key] = value

                if alt_service_key:
                    merged_conf[alt_service_key] = value

    if errors:
        raise ValueError("\n".join(errors))

    provider.conf(merged_conf)

    return provider
