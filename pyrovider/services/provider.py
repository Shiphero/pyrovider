import os

from dotenv import find_dotenv, load_dotenv
from pyrovider.meta.ioc import Importer
from pyrovider.tools.dicttools import dictpath
from werkzeug import Local, release_local

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


class ServiceProvider():

    UNKNOWN_SERVICE_ERRMSG = '"{}" is not a service we know of.'
    TOO_MANY_CREATION_METHODS_ERRMSG = 'You must define either a class, an instance, ' \
                                       'or a factory for the service "{}", not both.'
    NO_CREATION_METHOD_ERRMSG = 'You must define either a class, an instance, or ' \
                                'a factory for the service "{}", none was found.'
    NOT_A_SERVICE_FACTORY_ERRMSG = 'The factory class for the service ' \
                                   '"{}" does not have a "build" method.'
    BAD_CONF_PATH_ERRMSG = 'The path "{}" was not found in the app configuration.'

    _service_meths = {'instance': '_get_service_instance',
                      'class': '_instance_service_with_class',
                      'factory': '_instance_service_with_factory'}

    _local = Local()

    def __init__(self):
        self.importer = Importer()  # Can't inject it, obviously.
        self.service_conf = {}
        self.app_conf = {}

    def _init_local(self):
        if not hasattr(self._local, 'set_services'):
            self._local.set_services = {}
            self._local.service_instances = {}
            self._local.service_classes = {}
            self._local.factory_classes = {}

    def reset(self):
        release_local(self._local)

    def __del__(self):
        self.reset()        


    def conf(self, service_conf, app_conf=None):
        if app_conf is None:
            app_conf = {}

        self.service_conf = service_conf
        self.app_conf = app_conf

    def get(self, name, **kwargs):
        self._init_local()

        if name not in self.service_conf:
            raise UnknownServiceError(self.UNKNOWN_SERVICE_ERRMSG.format(name))

        return self._get_set_service(name) or self._get_built_service(name, **kwargs)

    def _get_set_service(self, name):
        if name in self._local.set_services:
            return self._local.set_services[name]

    def _get_built_service(self, name, **kwargs):
        if self.service_conf[name] and self._has_multiple_creation_methods(name):
            raise TooManyCreationMethodsError(self.TOO_MANY_CREATION_METHODS_ERRMSG.format(name))

        for service_type, method in self._service_meths.iteritems():
            if self.service_conf[name] and service_type in self.service_conf[name]:
                return getattr(self, method)(name, **kwargs)
        else:
            raise NoCreationMethodError(self.NO_CREATION_METHOD_ERRMSG.format(name))

    def set(self, name, service):
        self._init_local()

        if name not in self.service_conf:
            raise UnknownServiceError(self.UNKNOWN_SERVICE_ERRMSG.format(name))

        self._local.set_services[name] = service

    def _has_multiple_creation_methods(self, name):
        if not self.service_conf[name]:
            raise NoCreationMethodError(self.NO_CREATION_METHOD_ERRMSG.format(name))

        return 1 < len([k for k in self._service_meths.keys() if k in self.service_conf[name]])

    def _get_service_instance(self, name):
        if name not in self._local.service_instances:
            self._local.service_instances[name] = self.importer.get_obj(self.service_conf[name]['instance'])

        return self._local.service_instances[name]

    def _instance_service_with_class(self, name, **kwargs):
        if name not in self._local.service_classes:
            self._local.service_classes[name] = self.importer.get_obj(self.service_conf[name]['class'])

        return self._local.service_classes[name](*self._get_args(name), **self._get_kwargs(name, **kwargs))

    def _instance_service_with_factory(self, name, **kwargs):
        if name not in self._local.factory_classes:
            factory_class = self.importer.get_obj(self.service_conf[name]['factory'])

            if not hasattr(factory_class, 'build') or not callable(factory_class.build):
                raise NotAServiceFactoryError(self.NOT_A_SERVICE_FACTORY_ERRMSG.format(name))

            self._local.factory_classes[name] = factory_class

        return self._local.factory_classes[name](*self._get_args(name), **self._get_kwargs(name, **kwargs)).build()

    def _get_args(self, name):
        if 'arguments' in self.service_conf[name]:
            return [self._get_arg(ref) for ref in self.service_conf[name]['arguments']]
        else:
            return []

    def _get_kwargs(self, name, **kwargs):
        named_arguments = {}

        for k, v in self.service_conf[name].get('named_arguments', {}).items():
            named_arguments[k] = kwargs.get(k, None) or self._get_arg(v)

        return named_arguments

    def _get_arg(self, ref):
        if isinstance(ref, str):
            if '@' == ref[0]:
                return self.get(ref[1:])
            elif '%' == ref[0] == ref[-1:]:
                return self._get_conf(ref[1:-1])
            elif '$' == ref[0]:
                return self._get_env(ref[1:-1])
            elif '^' == ref[0]:
                return self.importer.get_obj(ref[1:])
        elif isinstance(ref, list):
            if '$' == ref[0][0]:
                return self._get_env(ref[0][1:], ref[1])
            else:
                return [self._get_arg(i) for i in ref]

        return ref  # Literal

    def _get_conf(self, path):
        parts = path.split('.')

        try:
            trunk = self.app_conf[parts[0]]
        except KeyError as e:
            raise BadConfPathError(self.BAD_CONF_PATH_ERRMSG.format(parts[0]))

        try:
            return dictpath(trunk, parts[1:])
        except KeyError as e:
            raise BadConfPathError(self.BAD_CONF_PATH_ERRMSG.format(e.args[0]))

    def _get_env(self, var, default=None):
        default = self._get_arg(default)

        return os.environ.get(var, default)
