import importlib.metadata

from pyrovider.services.factories import (
    service_provider_from_directory,
    service_provider_from_yaml,
    split_service_definitions,
)

__all__ = ["service_provider_from_directory", "service_provider_from_yaml", "split_service_definitions"]

try:
    __version__ = importlib.metadata.version("pyrovider")
except Exception:
    __version__ = "UNKNOWN"
