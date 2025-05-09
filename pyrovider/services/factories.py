import typing
from pathlib import Path

import yaml

from .provider import ServiceProvider


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

    with open(service_conf_path) as fp:
        service_conf = yaml.full_load(fp.read())

    if app_conf_path is not None:
        with open(app_conf_path) as fp:
            app_conf = yaml.full_load(fp.read())
    else:
        app_conf = None

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

    for source in sources:
        if not isinstance(source, ServiceDefinitionSource):
            raise TypeError(f"source must be a {ServiceDefinitionSource.__name__} instance")

        with open(source.path) as fp:
            service_conf = yaml.full_load(fp.read())

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
