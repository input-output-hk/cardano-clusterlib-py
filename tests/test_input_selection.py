"""Reservations apply to shared input selection independently of sub-transactions."""

import dataclasses
from types import SimpleNamespace
from unittest import mock

import pytest

from cardano_clusterlib import exceptions
from cardano_clusterlib import structs
from cardano_clusterlib import txtools


@pytest.fixture
def cluster() -> SimpleNamespace:
    return SimpleNamespace(
        g_query=mock.Mock(),
        g_transaction=mock.Mock(),
        _min_change_value=1_800_000,
    )


@pytest.fixture
def reserved() -> structs.UTXOData:
    return structs.UTXOData(utxo_hash="reserved", utxo_ix=0, amount=20_000_000, address="source")


@pytest.mark.parametrize(argnames="cached", argvalues=[False, True])
@pytest.mark.parametrize(argnames="collect", argvalues=[False, True])
def test_exclude_all_assets_of_reserved_input(
    cluster: SimpleNamespace,
    reserved: structs.UTXOData,
    cached: bool,
    collect: bool,
) -> None:
    token = dataclasses.replace(reserved, coin="token", amount=1)
    # The same hash at a different output index must remain spendable.
    funding = dataclasses.replace(reserved, utxo_ix=1)
    candidates = [reserved, token, funding]
    cluster.g_query.get_utxo.return_value = candidates
    kwargs = {
        "clusterlib_obj": cluster,
        "src_address": "source",
        "deposit": 0,
        "fee": 200_000,
        "reserved_txins": [token],
        "src_addr_utxos": candidates if cached else None,
    }
    if collect:
        inputs = txtools.collect_data_for_build(**kwargs).txins
    else:
        inputs, __ = txtools._get_tx_ins_outs(tx_files=structs.TxFiles(), **kwargs)
    assert inputs == [funding]
    if cached:
        cluster.g_query.get_utxo.assert_not_called()
    else:
        cluster.g_query.get_utxo.assert_called_once_with(address="source")
    assert candidates == [reserved, token, funding]


@pytest.mark.parametrize(argnames="cached", argvalues=[False, True])
def test_all_candidates_reserved_do_not_trigger_fallback(
    cluster: SimpleNamespace,
    reserved: structs.UTXOData,
    cached: bool,
) -> None:
    cluster.g_query.get_utxo.return_value = [reserved]
    with pytest.raises(expected_exception=exceptions.CLIError, match="No unreserved UTxO"):
        txtools._get_tx_ins_outs(
            clusterlib_obj=cluster,
            src_address="source",
            tx_files=structs.TxFiles(),
            reserved_txins=[reserved],
            src_addr_utxos=[reserved] if cached else None,
        )
    if cached:
        cluster.g_query.get_utxo.assert_not_called()
    else:
        cluster.g_query.get_utxo.assert_called_once_with(address="source")


def test_empty_cache_does_not_query(cluster: SimpleNamespace, reserved: structs.UTXOData) -> None:
    cluster.g_query.get_utxo.return_value = [reserved]
    with pytest.raises(expected_exception=exceptions.CLIError, match="No UTxO returned"):
        txtools.collect_data_for_build(
            clusterlib_obj=cluster,
            src_address="source",
            src_addr_utxos=[],
            reserved_txins=[reserved],
        )
    cluster.g_query.get_utxo.assert_not_called()


def test_explicit_inputs_are_unchanged(
    cluster: SimpleNamespace, reserved: structs.UTXOData
) -> None:
    inputs, __ = txtools._get_tx_ins_outs(
        clusterlib_obj=cluster,
        src_address="source",
        tx_files=structs.TxFiles(),
        txins=[reserved],
        reserved_txins=[reserved],
        src_addr_utxos=[],
        deposit=0,
        fee=200_000,
    )
    assert inputs == [reserved]
    cluster.g_query.get_utxo.assert_not_called()


def test_select_more_unreserved_inputs(
    cluster: SimpleNamespace, reserved: structs.UTXOData
) -> None:
    funding = [dataclasses.replace(reserved, utxo_ix=index, amount=4_000_000) for index in (1, 2)]
    cluster.g_query.get_utxo.return_value = [reserved, *funding]
    amount = 5_000_000
    fee = 200_000
    result = txtools.collect_data_for_build(
        clusterlib_obj=cluster,
        src_address="source",
        reserved_txins=[reserved],
        txouts=[structs.TxOut(address="destination", amount=amount)],
        fee=fee,
        deposit=0,
    )
    assert result.txins == funding
    assert result.txouts == [
        structs.TxOut(address="destination", amount=amount),
        structs.TxOut(address="source", amount=sum(t.amount for t in funding) - amount - fee),
    ]
    cluster.g_query.get_utxo.assert_called_once_with(address="source")
