from unittest.mock import MagicMock



def selector(key: str):
    return key


class ServiceA(MagicMock):
    pass


class ServiceB(MagicMock):
    pass


class ServiceC(MagicMock):
    pass