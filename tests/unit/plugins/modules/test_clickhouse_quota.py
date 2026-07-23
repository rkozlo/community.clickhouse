from __future__ import absolute_import, division, print_function

__metaclass__ = type
import pytest
from ansible_collections.community.clickhouse.plugins.modules.clickhouse_quota import (
    ClickHouseQuota,
    _DEFAULT_PARAMS as DEFAULT_NORMALIZE_PARAMS,
)


@pytest.fixture
def quota(mocker):
    mock_module = mocker.MagicMock()
    mock_module.check_mode = False
    mock_client = mocker.MagicMock()

    return ClickHouseQuota(module=mock_module, client=mock_client, name="test_quota")


def test_setup_object(quota):
    assert quota.name == 'test_quota'
    assert quota._exists is None


def test_not_exists_loading(quota, mocker):
    mocker.patch(
        "ansible_collections.community.clickhouse.plugins.modules.clickhouse_quota.execute_query",
        return_value=[])
    assert quota.exists is False
    assert quota._loaded is False
    assert quota.keyed_by is None
    assert quota.durations is None
    assert quota.apply_to_all is None
    assert quota.apply_to_except is None
    assert quota._quota_limits == []


def test_exists_loading(quota, mocker):
    mocker.patch(
        "ansible_collections.community.clickhouse.plugins.modules.clickhouse_quota.execute_query",
        return_value=[(['user_name'], [3600], 0, ['test'], ['except'])])
    assert quota.exists is True
    assert quota._loaded is False
    assert quota.keyed_by == ['user_name']
    assert quota.durations == [3600]
    assert quota.apply_to_all == 0
    assert quota.apply_to_list == ['test']
    assert quota.apply_to_except == ['except']
    assert quota._quota_limits == []


def test_properties_loading_empty_limit(quota, mocker):
    mocker.patch(
        "ansible_collections.community.clickhouse.plugins.modules.clickhouse_quota.execute_query",
        return_value=[(['user_name'], [], 0, ['test'], ['except'])])
    assert quota.exists is True
    assert quota._loaded is True


def test_properties_loading(quota, mocker):
    mocker.patch(
        "ansible_collections.community.clickhouse.plugins.modules.clickhouse_quota.execute_query",
        return_value=[(3600, 0, None, None, None, None, None, None, None, None, None, None, None)])
    quota._load()
    assert quota._loaded is True
    assert quota.quota_limits == [{
        "max": {
            "queries": None,
            "query_selects": None,
            "query_inserts": None,
            "errors": None,
            "result_rows": None,
            "result_bytes": None,
            "read_rows": None,
            "read_bytes": None,
            "written_bytes": None,
            "execution_time": None,
            "failed_sequential_authentications": None,
        },
        "randomized_start": False,
        "interval": 3600,
        "tracking_only": True,
    }]


def test_properties_loading_check_quota_limits(quota, mocker):
    mocker.patch(
        "ansible_collections.community.clickhouse.plugins.modules.clickhouse_quota.execute_query",
        return_value=[(3600, 0, 1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009.0, 1010)]
    )
    assert quota.quota_limits == [{
        "max": {
            "queries": 1000,
            "query_selects": 1001,
            "query_inserts": 1002,
            "errors": 1003,
            "result_rows": 1004,
            "result_bytes": 1005,
            "read_rows": 1006,
            "read_bytes": 1007,
            "written_bytes": 1008,
            "execution_time": 1009.0,
            "failed_sequential_authentications": 1010,
        },
        "randomized_start": False,
        "interval": 3600,
    }]


@pytest.mark.parametrize(
    'input,expected',
    [
        ("1 second", 1),
        ("1 SECOND", 1),
        ("2 second", 2),
        ("1 minute", 60),
        ("2 minute", 120),
        ("2 hour", 7200),
        ("2 day", 172800),
        ("2 week", 1209600),
        ("2 month", 5259492),
        ("2 quarter", 15778476),
        ("2 year", 63113904),
    ]
)
def test_normalize_interval(quota, input, expected):
    result = quota._normalize_interval(input)
    assert result == expected
    quota.module.fail_json.assert_not_called()


@pytest.mark.parametrize(
    argnames="params,expected",
    argvalues=[
        ({}, {}),
        (
            {"apply_to": ["test_user", "current_user"]},
            {"apply_to": ["current_user", "test_user"]},
        ),
        ({"apply_to_mode": "all_except_listed"}, {"apply_to_mode": "all"}),
        ({"extra_args": "foo"}, {}),
        ({"keyed_by": "user_name"}, {"keyed_by": "user_name"}),
        ({"keyed_by": "client_key,user_name"}, {"keyed_by": "client_key,user_name"}),
        ({"keyed_by": "client_key, user_name"}, {"keyed_by": "client_key,user_name"}),
        (
            {"limits": [{"interval": "5 minute"}, {"interval": "1 minute"}]},
            {
                "limits": [
                    {
                        "interval": 60,
                        "randomized_start": False,
                        "max": {},
                        "no_limits": None,
                        "tracking_only": None,
                    },
                    {
                        "interval": 300,
                        "randomized_start": False,
                        "max": {},
                        "no_limits": None,
                        "tracking_only": None,
                    },
                ]
            },
        ),
        (
            {
                "limits": [
                    {
                        "interval": "1 day",
                        "max": {
                            "queries": 10,
                        },
                    }
                ]
            },
            {
                "limits": [
                    {
                        "randomized_start": False,
                        "interval": 86400,
                        "max": {
                            "queries": 10,
                            "query_selects": None,
                            "query_inserts": None,
                            "errors": None,
                            "result_rows": None,
                            "result_bytes": None,
                            "read_rows": None,
                            "read_bytes": None,
                            "written_bytes": None,
                            "execution_time": None,
                            "failed_sequential_authentications": None,
                        },
                        "no_limits": None,
                        "tracking_only": None,
                    }
                ]
            },
        ),
        (
            {
                "limits": [
                    {
                        "interval": "1 day",
                        "max": {
                            "errors": 1,
                        },
                    }
                ]
            },
            {
                "limits": [
                    {
                        "randomized_start": False,
                        "interval": 86400,
                        "max": {
                            "errors": 1,
                            "queries": None,
                            "query_selects": None,
                            "query_inserts": None,
                            "result_rows": None,
                            "result_bytes": None,
                            "read_rows": None,
                            "read_bytes": None,
                            "written_bytes": None,
                            "execution_time": None,
                            "failed_sequential_authentications": None,
                        },
                        "no_limits": None,
                        "tracking_only": None,
                    }
                ]
            },
        ),
        (
            {
                "limits": [
                    {
                        "interval": "1 day",
                        "no_limits": True,
                    }
                ]
            },
            {"limits": []},
        ),
        (
            {
                "limits": [
                    {
                        "interval": "1 day",
                        "tracking_only": True,
                    }
                ]
            },
            {
                "limits": [
                    {
                        "randomized_start": False,
                        "interval": 86400,
                        "max": {},
                        "no_limits": None,
                        "tracking_only": True,
                    }
                ]
            },
        ),
        ({"limits": None}, {"limits": []}),
        ({"apply_to": None}, {"apply_to": []}),
        (
            {
                "limits": [
                    {
                        "interval": "15 minute",
                        "max": None,
                        "no_limits": None,
                        "tracking_only": True,
                        "random_extra_key": True,
                    }
                ]
            },
            {
                "limits": [
                    {
                        "interval": 900,
                        "max": {},
                        "no_limits": None,
                        "tracking_only": True,
                        "randomized_start": False,
                    }
                ]
            },
        ),
    ],
)
def test_normalize(params, expected, quota):
    actual = quota._normalize(params)
    assert actual == (DEFAULT_NORMALIZE_PARAMS | expected)
