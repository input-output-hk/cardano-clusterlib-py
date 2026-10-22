"""Guard records and formatting shared by transaction builders."""

import pytest

from cardano_clusterlib import clusterlib
from cardano_clusterlib import structs
from cardano_clusterlib import txtools


@pytest.mark.parametrize(
    argnames="field",
    argvalues=[
        "verification_key",
        "verification_key_file",
        "key_hash",
        "script_hash",
        "script_file",
    ],
)
@pytest.mark.parametrize(argnames="required_top_level", argvalues=[False, True])
def test_guard_sources(field: str, required_top_level: bool) -> None:
    guard_type = structs.RequiredTopLevelGuard if required_top_level else structs.TxGuard
    guard = guard_type(**{field: "source"})
    prefix = "--top-level-guard" if required_top_level else "--guard"
    assert txtools._get_guard_args(guard) == [f"{prefix}-{field.replace('_', '-')}", "source"]


@pytest.mark.parametrize(argnames="kind", argvalues=["file", "cbor_file", "value"])
def test_guard_data(kind: str) -> None:
    local = structs.TxGuard(script_hash="hash", execution_units=(0, 0), **{f"redeemer_{kind}": "0"})
    top = structs.RequiredTopLevelGuard(script_hash="hash", **{f"datum_{kind}": "0"})
    assert txtools._get_guard_args(local)[-2:] == [
        f"--guard-redeemer-{kind.replace('_', '-')}",
        "0",
    ]
    assert txtools._get_guard_args(top)[-2:] == [
        f"--top-level-guard-datum-{kind.replace('_', '-')}",
        "0",
    ]


@pytest.mark.parametrize(
    argnames="guard",
    argvalues=[
        structs.TxGuard(),
        structs.TxGuard(key_hash="a", script_hash="b"),
        structs.TxGuard(key_hash="a", redeemer_value="0", execution_units=(0, 0)),
        structs.TxGuard(script_hash="a", redeemer_value="0"),
        structs.TxGuard(script_hash="a", execution_units=(0, 0)),
        structs.RequiredTopLevelGuard(key_hash="a", datum_value="0"),
    ],
)
def test_invalid_guard(guard: structs.TxGuard | structs.RequiredTopLevelGuard) -> None:
    with pytest.raises(expected_exception=ValueError, match=r"guard|Guard"):
        txtools._get_guard_args(guard)


def test_public_exports() -> None:
    assert clusterlib.TxGuard is structs.TxGuard
    assert clusterlib.RequiredTopLevelGuard is structs.RequiredTopLevelGuard
