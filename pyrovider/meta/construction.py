# TODO: A class cannot extend another class when using this as meta.
import typing


class Singleton(type):
    """
    As the metaclass of a class, it turns it into a singleton.
    """

    _instances: typing.ClassVar = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)

        return cls._instances[cls]
