import importlib.metadata
from pyrovider.services.factories import service_provider_from_yaml

__all__ = ["service_provider_from_yaml"]

try:
    __version__ = importlib.metadata.version("pyrovider")
except Exception:
    __version__ = "UNKNOWN"
