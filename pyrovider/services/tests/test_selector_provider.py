import pytest

from pyrovider.services.provider import ServiceProvider, MissingParameter, ServiceSelector


@pytest.mark.parametrize(
    "selector, is_bool, default, key, options, expected_service",
    [
        (
            lambda k: "v1",
            False,
            "default-service",
            "xxx",
            dict(v1="service-1", v2="service-2"),
            "service-1",
        ),
        (
            lambda k: "zzzz",
            False,
            "default-service",
            "xxx",
            dict(v1="service-1", v2="service-2"),
            "default-service",
        ),
        (
            lambda k: True,
            True,
            "default-service",
            "xxx",
            dict(on="service-1", off="service-2"),
            "service-1",
        ),
        (
            lambda k: False,
            True,
            "default-service",
            "xxx",
            dict(on="service-1", off="service-2"),
            "service-2",
        ),
        (
            lambda k: None,
            True,
            "default-service",
            "xxx",
            dict(on="service-1"),
            "default-service",
        )
    ],
    ids=[
        "selection-value-matches-options",
        "selection-value-doesnt-match-options-uses-default",
        "selection-is-bool-matches-on-flag",
        "selection-is-bool-matches-off-flag",
        "selection-is-bool-not-match-uses-default",
    ],
)
def test_get_service(selector, is_bool, default, key, options, expected_service):
    selector_service = ServiceSelector("test", selector=selector, key=key, default=default, is_bool=is_bool, **options)
    service_name = selector_service()
    assert service_name == expected_service


@pytest.mark.parametrize(
    "selector, is_bool, default, key, options, expected_error",
    [
        (
            lambda k: "v1",
            False,
            None,
            "xxx",
            dict(v1="service-1", v2="service-2"),
            "requires a default service",
        ),
        (
            lambda k: "zzzz",
            False,
            "default-service",
            "xxx",
            dict(),
            "requires a service options to be defined",
        ),
        (
            lambda k: True,
            True,
            "default-service",
            "xxx",
            dict(off="service-2"),
            "requires a value for the 'on' parameter",
        ),
    ],
    ids=[
        "missing-default-service",
        "missing-options",
        "missing-on-service-for-bool-selector",
    ],
)
def test_bad_config(selector, is_bool, default, key, options, expected_error):
    with pytest.raises(MissingParameter) as e:
        selector_service = ServiceSelector("test", selector=selector, key=key, default=default, is_bool=is_bool, **options)
        assert expected_error in str(e)


@pytest.mark.parametrize(
    "conf, expected_service",
    [
        (
            {
                "test.version-1": {
                    "class": "pyrovider.services.tests.mocks.ServiceA"
                },
                "test.version-2": {
                    "class": "pyrovider.services.tests.mocks.ServiceB"
                },
                "test.version-3": {
                    "class": "pyrovider.services.tests.mocks.ServiceC"
                },
                "test": {
                    "selector": "pyrovider.services.tests.mocks.selector",
                    "named_arguments": {
                        "default": "test.version-1",
                        "key": "v1",
                        "v1": "test.version-1",
                        "v2": "test.version-2",
                        "v3": "test.version-3",
                    }
                }
            },
            "test.version-1",
        ),
    ],
)
def test_getting_available_namespaces(conf: dict, expected_service):
    provider = ServiceProvider()
    provider.conf(conf)

    assert provider.get(expected_service).__class__.__name__ == provider.get("test").__class__.__name__

