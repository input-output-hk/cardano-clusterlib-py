"""Regression tests for old and new pool query JSON formats."""

import json
import warnings
from unittest import mock

import pytest

from cardano_clusterlib import query_group
from cardano_clusterlib import structs


@pytest.mark.parametrize("field", ["pParams pState", "stakePools"])
@pytest.mark.parametrize("pools", [{}, {"pool-id": {"spsPledge": 100}}])
def test_registered_stake_pools(field: str, pools: dict) -> None:
    """Read registered pools from both ledger state formats, including empty maps."""
    queries = query_group.QueryGroup(mock.Mock())
    ledger = {"stateBefore": {"esLState": {"delegationState": {"pstate": {field: pools}}}}}
    with mock.patch.object(queries, "get_ledger_state", return_value=ledger):
        assert queries.get_registered_stake_pools_ledger_state() == pools


def test_empty_new_registered_stake_pools() -> None:
    """Do not fall back to legacy pools when the new map exists but is empty."""
    queries = query_group.QueryGroup(mock.Mock())
    pool_state = {"stakePools": {}, "pParams pState": {"old-pool": {}}}
    ledger = {"stateBefore": {"esLState": {"delegationState": {"pstate": pool_state}}}}
    with mock.patch.object(queries, "get_ledger_state", return_value=ledger):
        assert queries.get_registered_stake_pools_ledger_state() == {}


@pytest.mark.parametrize("method", ["get_pool_params", "get_pool_state"])
@pytest.mark.parametrize(
    ("record", "expected"),
    [
        (
            {"poolParams": {"pledge": 100}, "futurePoolParams": {"pledge": 200}, "retiring": 12},
            structs.PoolParamsTop(
                pool_params={"pledge": 100}, future_pool_params={"pledge": 200}, retiring=12
            ),
        ),
        (
            {"poolParams": {"spsPledge": 100}, "futurePoolParams": None, "retiring": None},
            structs.PoolParamsTop(
                pool_params={"spsPledge": 100}, future_pool_params={}, retiring=None
            ),
        ),
        (
            {
                "pledge": 100,
                "blsKey": {"bksKey": {"blsPubKey": "bls-key"}},
                "futureStakePoolParams": {"sppPledge": 200},
                "retiring": "12",
            },
            structs.PoolParamsTop(
                pool_params={"pledge": 100, "blsKey": {"bksKey": {"blsPubKey": "bls-key"}}},
                future_pool_params={"sppPledge": 200},
                retiring=12,
            ),
        ),
        (
            {"pledge": 100, "futureStakePoolParams": None, "retiring": None},
            structs.PoolParamsTop(
                pool_params={"pledge": 100}, future_pool_params={}, retiring=None
            ),
        ),
        (
            {"poolParams": None, "futurePoolParams": None, "retiring": None},
            structs.PoolParamsTop(pool_params={}, future_pool_params={}, retiring=None),
        ),
        ({}, structs.PoolParamsTop(pool_params={}, future_pool_params={}, retiring=None)),
    ],
)
def test_pool_queries(method: str, record: dict, expected: structs.PoolParamsTop) -> None:
    """Normalize old nested and new flattened records without changing query output."""
    queries = query_group.QueryGroup(mock.Mock())
    response = {"pool-id": record}
    with (
        mock.patch.object(queries, "query_cli", return_value=json.dumps(response)) as query,
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("ignore", DeprecationWarning)
        assert getattr(queries, method)(stake_pool_id="pool-id") == expected
    query.assert_called_once_with(
        [method.removeprefix("get_").replace("_", "-"), "--stake-pool-id", "pool-id"]
    )


@pytest.mark.parametrize("method", ["get_pool_params", "get_pool_state"])
def test_unknown_pool(method: str) -> None:
    """Return empty parameters for queries with no matching pool."""
    queries = query_group.QueryGroup(mock.Mock())
    with (
        mock.patch.object(queries, "query_cli", return_value="{}"),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("ignore", DeprecationWarning)
        assert getattr(queries, method)(stake_pool_id="unknown-pool") == structs.PoolParamsTop(
            pool_params={}, future_pool_params={}, retiring=None
        )


def test_legacy_unnested_pool_params() -> None:
    """Keep support for pool parameters returned without an outer pool ID."""
    queries = query_group.QueryGroup(mock.Mock())
    record = {"poolParams": {"pledge": 100}, "futurePoolParams": {}, "retiring": None}
    with (
        mock.patch.object(queries, "query_cli", return_value=json.dumps(record)),
        pytest.warns(DeprecationWarning, match="`pool-params` deprecated"),
    ):
        assert queries.get_pool_params(stake_pool_id="pool-id") == structs.PoolParamsTop(
            pool_params={"pledge": 100}, future_pool_params={}, retiring=None
        )
