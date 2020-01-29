import os

from collections import defaultdict

from dotenv import find_dotenv, load_dotenv
from pyrovider.meta.construction import Singleton
from pyrovider.meta.ioc import Importer
from pyrovider.tools.dicttools import dictpath

# Loads env vars from .env file
load_dotenv(find_dotenv())


class ServiceProviderError(Exception):

    pass


class UnknownServiceError(ServiceProviderError):

    pass


class TooManyCreationMethodsError(ServiceProviderError):

    pass


class NoCreationMethodError(ServiceProviderError):

    pass


class NotAServiceFactoryError(ServiceProviderError):

    pass


class BadConfPathError(ServiceProviderError):

    pass


class ServiceFactory():

    def build(self):
        raise NotImplementedError()


def get_services_and_namespaces(services_names, provider):
    services = []
    namespaces = {}
    namespace_map = defaultdict(list)

    for key in services_names:
        parts = key.split(".")
        namespace = parts[0] if len(parts) > 1 else None
        service_name = ".".join(parts[1:])
        if namespace:
            namespace_map[namespace].append(service_name)
        else:
            services.append(key)
    for namespace, namespace_service_names in namespace_map.items():
        namespaces[namespace] = Namespace(namespace, namespace_service_names, provider)

    return services, namespaces


class Namespace:

    def __init__(self, name, services_names, provider):
        self.name = name
        self.provider = provider

        services, namespaces = get_services_and_namespaces(services_names, provider)
        self._service_names = services
        self._namespaces = namespaces

    def __getattr__(self, key):
        if key in self._namespaces:
            return self._namespaces[key]

        elif key in self._service_names:
            return self.get(key)

        raise AttributeError(f"Unknown attribute or service '{key}'")

    def get(self, name, **kwargs):
        return self.provider.get(f"{self.name}.{name}", **kwargs)

    def set(self, name: str, service: any):
        return self.provider.set(f"{self.name}.{name}", service)

    @property
    def namespaces(self):
        return self._namespaces.keys()

    @property
    def service_names(self):
        return self._service_names


# class ServiceProvider():
class ServiceProvider(metaclass=Singleton):

    UNKNOWN_SERVICE_ERRMSG = '"{}" is not a service we know of.'
    TOO_MANY_CREATION_METHODS_ERRMSG = 'You must define either a class, an instance, ' \
                                       'or a factory for the service "{}", not both.'
    NO_CREATION_METHOD_ERRMSG = 'You must define either a class, an instance, or ' \
                                'a factory for the service "{}", none was found.'
    NOT_A_SERVICE_FACTORY_ERRMSG = 'The factory class for the service ' \
                                   '"{}" does not have a "build" method.'
    BAD_CONF_PATH_ERRMSG = 'The path "{}" was not found in the app configuration.'

    _service_meths = {
        'instance': '_get_service_instance',
        'class': '_instance_service_with_class',
        'factory': '_instance_service_with_factory'
    }

    def __init__(self):
        self.importer = Importer()  # Can't inject it, obviously.
        self.service_conf = {}
        self.app_conf = {}
        self.set_services = {}
        self.service_instances = {}
        self.service_classes = {}
        self.factory_classes = {}
        self._namespaces = {}
        self._service_names = []

    def reset(self):
        self.set_services = {}
        self.service_instances = {}
        self.service_classes = {}
        self.factory_classes = {}

    def conf(self, service_conf: dict, app_conf: dict = None):
        if app_conf is None:
            app_conf = {}

        self.service_conf = service_conf
        self.app_conf = app_conf

        service_names, namespaces = get_services_and_namespaces(service_conf.keys(), self)
        self._service_names = service_names
        self._namespaces = namespaces

    @property
    def namespaces(self):
        return self._namespaces.keys()

    @property
    def service_names(self):
        return self._service_names

    def __getattr__(self, key):
        if key in self._namespaces:
            return self._namespaces[key]

        elif key in self._service_names:
            return self.get(key)

        raise AttributeError(f"Unknown attribute, service or namespace '{key}'")

    def get(self, name: str, **kwargs):
        if name not in self.service_conf:
            raise UnknownServiceError(self.UNKNOWN_SERVICE_ERRMSG.format(name))

        return self._get_set_service(name) or self._get_built_service(name, **kwargs)

    def _get_set_service(self, name: str):
        return self.set_services.get(name)

    def _get_built_service(self, name: str, **kwargs):
        if self.service_conf[name] and self._has_multiple_creation_methods(name):
            raise TooManyCreationMethodsError(self.TOO_MANY_CREATION_METHODS_ERRMSG.format(name))

        for service_type, method in self._service_meths.items():
            if self.service_conf[name] and service_type in self.service_conf[name]:
                return getattr(self, method)(name, **kwargs)
        else:
            raise NoCreationMethodError(self.NO_CREATION_METHOD_ERRMSG.format(name))

    def set(self, name: str, service: any):
        if name not in self.service_conf:
            raise UnknownServiceError(self.UNKNOWN_SERVICE_ERRMSG.format(name))

        self.set_services[name] = service

    def _has_multiple_creation_methods(self, name: str):
        if not self.service_conf[name]:
            raise NoCreationMethodError(self.NO_CREATION_METHOD_ERRMSG.format(name))

        return 1 < len([k for k in self._service_meths.keys() if k in self.service_conf[name]])

    def _get_service_instance(self, name: str):
        if name not in self.service_instances:
            self.service_instances[name] = self.importer.get_class(self.service_conf[name]['instance'])

        return self.service_instances[name]

    def _instance_service_with_class(self, name: str, **kwargs):
        if name not in self.service_classes:
            self.service_classes[name] = self.importer.get_class(self.service_conf[name]['class'])

        return self.service_classes[name](*self._get_args(name), **self._get_kwargs(name, **kwargs))

    def _instance_service_with_factory(self, name: str, **kwargs):
        if name not in self.factory_classes:
            factory_class = self.importer.get_class(self.service_conf[name]['factory'])

            if not hasattr(factory_class, 'build') or not callable(factory_class.build):
                raise NotAServiceFactoryError(self.NOT_A_SERVICE_FACTORY_ERRMSG.format(name))

            self.factory_classes[name] = factory_class

        return self.factory_classes[name](*self._get_args(name), **self._get_kwargs(name, **kwargs)).build()

    def _get_args(self, name: str):
        if 'arguments' in self.service_conf[name]:
            return [self._get_arg(ref) for ref in self.service_conf[name]['arguments']]
        else:
            return []

    def _get_kwargs(self, name: str, **kwargs):
        named_arguments = {}

        for k, v in self.service_conf[name].get('named_arguments', {}).items():
            named_arguments[k] = kwargs.get(k, None) or self._get_arg(v)

        return named_arguments

    def _get_arg(self, ref: any):
        if isinstance(ref, str):
            if '@' == ref[0]:
                return self.get(ref[1:])
            elif '%' == ref[0] == ref[-1:]:
                return self._get_conf(ref[1:-1])
            elif '$' == ref[0]:
                return self._get_env(ref[1:-1])
            elif '^' == ref[0]:
                return self.importer.get_class(ref[1:])

        elif isinstance(ref, list):
            if '$' == ref[0][0]:
                return self._get_env(ref[0][1:], ref[1])
            else:
                return [self._get_arg(i) for i in ref]

        return ref # Literal

    def _get_conf(self, path: str):
        parts = path.split('.')

        try:
            trunk = self.app_conf[parts[0]]
        except KeyError as e:
            raise BadConfPathError(self.BAD_CONF_PATH_ERRMSG.format(parts[0]))

        try:
            return dictpath(trunk, parts[1:])
        except KeyError as e:
            raise BadConfPathError(self.BAD_CONF_PATH_ERRMSG.format(e.args[0]))

    def _get_env(self, var: str, default: any = None):
        default = self._get_arg(default)

        return os.environ.get(var, default)
