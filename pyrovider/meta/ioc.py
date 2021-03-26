import re
import importlib
from .construction import Singleton


class Importer(metaclass=Singleton):

    @staticmethod
    def get_obj(class_path: str) -> type:
        """Get a class by its path."""
        module_parts = class_path.split('.')
        module_name = ".".join(module_parts[:-1])
        module = importlib.import_module(module_name)
        obj = module_parts[-1:][0]

        matches = re.findall(r'\["[\w-]+"]', obj)
        if matches:
            key = matches[0]
            dictionary = module.__dict__[obj[:-len(key)]]
            return dictionary[key[2:-2]]
        else:
            return module.__dict__[obj]
