"""Sub-transaction argument, accounting, and optional real-CLI smoke tests."""

import dataclasses
import json
import pathlib as pl
import shutil
import subprocess
from types import SimpleNamespace
from unittest import mock

import pytest

from cardano_clusterlib import consts
from cardano_clusterlib import exceptions
from cardano_clusterlib import query_group
from cardano_clusterlib import structs
from cardano_clusterlib import sub_transaction_group
from cardano_clusterlib import transaction_group
from cardano_clusterlib import txtools


def utxo(
    txhash: str = "a" * 64, amount: int = 10_000_000, coin: str = "lovelace"
) -> structs.UTXOData:
    return structs.UTXOData(utxo_hash=txhash, utxo_ix=0, amount=amount, address="source", coin=coin)


@pytest.fixture
def cluster(tmp_path: pl.Path) -> SimpleNamespace:
    def cli(args: list[str]) -> structs.CLIOut:
        if "--out-file" in args:
            pl.Path(args[args.index("--out-file") + 1]).touch()
        return structs.CLIOut(stdout=b"abc\n", stderr=b"")

    obj = SimpleNamespace(
        cli=mock.Mock(side_effect=cli),
        command_era="dijkstra",
        era_in_use="dijkstra",
        era_in_use_value=12,
        overwrite_outfiles=True,
        genesis={"protocolParams": {"minFeeB": 155381}},
        _min_change_value=1_800_000,
        create_pparams_file=mock.Mock(),
        pparams_file=tmp_path / "pparams.json",
        g_query=mock.Mock(),
        magic_args=[],
    )
    obj.g_sub_transaction = sub_transaction_group.SubTransactionGroup(obj)
    obj.g_transaction = transaction_group.TransactionGroup(obj)
    return obj


def test_build_and_embed(cluster: SimpleNamespace, tmp_path: pl.Path) -> None:
    child = cluster.g_sub_transaction.build_raw_tx_bare(
        out_file=tmp_path / "sub.body",
        txins=[utxo()],
        txouts=[structs.TxOut(address="destination", amount=8_000_000)],
        guards=[structs.TxGuard(key_hash="1" * 56)],
        invalid_before=0,
        invalid_hereafter=100,
        out_canonical_cbor=True,
    )
    assert child.txouts_count == 1
    assert "--invalid-before" in child.build_args
    assert "--out-canonical-cbor" in child.build_args
    assert "--fee" not in child.build_args
    signed = cluster.g_sub_transaction.sign_tx(
        sub_tx_file=child.out_file, tx_name="child", destination_dir=tmp_path
    )
    assert signed.name == "child_sub_tx.signed"
    assert "--signing-key-file" not in cluster.cli.call_args.args[0]
    parent = cluster.g_transaction.build_raw_tx_bare(
        out_file=tmp_path / "parent.body",
        txouts=[],
        tx_files=structs.TxFiles(),
        fee=200_000,
        txins=[utxo("b" * 64)],
        signed_sub_tx_files=[signed, "second.signed"],
        collateral_txins=[utxo("c" * 64)],
    )
    args = parent.build_args
    assert args[-4:] == [
        "--signed-sub-tx-file",
        str(signed),
        "--signed-sub-tx-file",
        "second.signed",
    ]
    assert "--tx-in-collateral" in args
    assert parent.txins == [utxo("b" * 64)]
    assert parent.signed_sub_tx_files == [signed, "second.signed"]
    assert cluster.cli.call_args_list[0].args[0] == ["sub-transaction", "--help"]


@pytest.mark.parametrize(argnames="signed", argvalues=[False, True])
def test_txid(cluster: SimpleNamespace, signed: bool) -> None:
    kwargs = {"signed_sub_tx_file" if signed else "sub_tx_file": "child"}
    assert cluster.g_sub_transaction.get_txid(**kwargs) == "abc"
    assert cluster.cli.call_args.args[0][-1] == "--output-text"


@pytest.mark.parametrize(
    argnames="kwargs", argvalues=[{}, {"sub_tx_file": "a", "signed_sub_tx_file": "b"}]
)
def test_txid_requires_one_file(cluster: SimpleNamespace, kwargs: dict) -> None:
    with pytest.raises(expected_exception=ValueError, match="exactly one"):
        cluster.g_sub_transaction.get_txid(**kwargs)


@pytest.mark.parametrize(argnames="era", argvalues=["conway", "latest"])
def test_unsupported_era(cluster: SimpleNamespace, era: str) -> None:
    cluster.command_era = era
    cluster.cli.side_effect = exceptions.CLIError("Invalid argument")
    with pytest.raises(expected_exception=exceptions.CLIError, match="unavailable"):
        cluster.g_sub_transaction.sign_tx(sub_tx_file="body", tx_name="test")


def test_guard_only_protocol_params(cluster: SimpleNamespace, tmp_path: pl.Path) -> None:
    output = cluster.g_sub_transaction.build_raw_tx_bare(
        out_file=tmp_path / "guard.body",
        txins=[utxo()],
        guards=[
            structs.TxGuard(script_file="v4.plutus", redeemer_value="0", execution_units=(0, 0))
        ],
    )
    cluster.create_pparams_file.assert_called_once()
    assert "--protocol-params-file" in output.build_args


def test_top_level_datum_does_not_need_protocol_params(
    cluster: SimpleNamespace,
    tmp_path: pl.Path,
) -> None:
    cluster.g_sub_transaction.build_raw_tx_bare(
        out_file=tmp_path / "requirement.body",
        txins=[utxo()],
        top_level_guards=[structs.RequiredTopLevelGuard(script_hash="hash", datum_value="0")],
    )
    cluster.create_pparams_file.assert_not_called()


@pytest.mark.parametrize(
    argnames="script_type",
    argvalues=["", consts.ScriptTypes.PLUTUS_V2, consts.ScriptTypes.PLUTUS_V3],
)
def test_reference_language_rejected(script_type: str) -> None:
    with pytest.raises(expected_exception=ValueError, match="explicit native or V4"):
        txtools._get_script_args(
            script_txins=[
                structs.ScriptTxIn(
                    txins=[utxo()], reference_txin=utxo("ref"), reference_type=script_type
                )
            ],
            mint=(),
            complex_certs=(),
            complex_proposals=(),
            script_withdrawals=(),
            script_votes=(),
            for_sub_transaction=True,
        )


def test_collateral_rejected() -> None:
    with pytest.raises(expected_exception=ValueError, match="cannot have collateral"):
        txtools._get_script_args(
            script_txins=[structs.ScriptTxIn(txins=[utxo()], collaterals=[utxo()])],
            mint=(),
            complex_certs=(),
            complex_proposals=(),
            script_withdrawals=(),
            script_votes=(),
            for_sub_transaction=True,
        )


def test_batch_balancing(cluster: SimpleNamespace, tmp_path: pl.Path) -> None:
    child = cluster.g_sub_transaction.build_raw_tx_bare(
        out_file=tmp_path / "child",
        txins=[utxo(amount=10_000_000)],
        txouts=[structs.TxOut(address="destination", amount=12_000_000)],
    )
    parent_input = utxo(txhash="b" * 64, amount=10_000_000)
    cluster.g_query.get_utxo.return_value = [utxo(), parent_input]
    result = cluster.g_transaction.build_raw_tx(
        src_address="source",
        tx_name="parent",
        fee=200_000,
        deposit=0,
        sub_transactions=[structs.SignedSubTx(out_file="signed", tx_raw_output=child)],
        destination_dir=tmp_path,
    )
    assert result.txins == [parent_input]
    expected_change = 7_800_000
    assert sum(t.amount for t in result.txouts) == expected_change
    assert "--signed-sub-tx-file" in result.build_args
    assert "--withdrawal" not in result.build_args


def test_batch_assets_and_deposits(tmp_path: pl.Path) -> None:
    child = structs.SubTxRawOutput(
        txins=[utxo(), utxo(amount=5, coin="token")],
        txouts=[
            structs.TxOut(address="dst", amount=8_000_000),
            structs.TxOut(address="dst", amount=7, coin="token"),
        ],
        txouts_count=1,
        tx_files=structs.TxFiles(certificate_files=["cert"]),
        out_file=tmp_path / "child",
        build_args=[],
        mint=[structs.Mint([structs.TxOut(address="", amount=4, coin="token")])],
        withdrawals=[structs.TxOut(address="stake", amount=1_000_000)],
        direct_deposits=[structs.TxOut(address="stake", amount=100_000)],
        treasury_donation=200_000,
    )
    with pytest.raises(expected_exception=ValueError, match="explicit net deposit"):
        txtools._get_sub_tx_balance([structs.SignedSubTx(out_file="signed", tx_raw_output=child)])
    balance, spent = txtools._get_sub_tx_balance(
        [structs.SignedSubTx(out_file="signed", tx_raw_output=child, deposit=2_000_000)]
    )
    assert balance == {"lovelace": 700_000, "token": 2}
    assert spent == {("a" * 64, 0)}
    with pytest.raises(expected_exception=ValueError, match="same input"):
        txtools._get_sub_tx_balance(
            [
                structs.SignedSubTx(out_file="one", tx_raw_output=child, deposit=0),
                structs.SignedSubTx(out_file="two", tx_raw_output=child, deposit=0),
            ]
        )


def test_file_only_manual_balancing(cluster: SimpleNamespace, tmp_path: pl.Path) -> None:
    inputs = [utxo()]
    outputs = [structs.TxOut(address="destination", amount=7_000_000)]
    files = [tmp_path / "second.signed", tmp_path / "first.signed"]
    with mock.patch.object(
        target=txtools,
        attribute="collect_data_for_build",
        side_effect=AssertionError("Manual mode must not balance"),
    ):
        result = cluster.g_transaction.build_raw_tx(
            src_address="unused",
            tx_name="manual",
            txins=inputs,
            txouts=outputs,
            fee=200_000,
            sub_transaction_files=files,
            destination_dir=tmp_path,
        )
    assert result.out_file.name == "manual_tx.body"
    assert result.txins == inputs
    assert result.txouts == outputs
    assert result.txouts_count == len(outputs)
    assert result.signed_sub_tx_files == files
    assert result.build_args[-4:] == [
        "--signed-sub-tx-file",
        str(files[0]),
        "--signed-sub-tx-file",
        str(files[1]),
    ]
    cluster.g_query.get_utxo.assert_not_called()
    cluster.g_query.get_protocol_params.assert_not_called()


@pytest.mark.parametrize(argnames="amount", argvalues=[-1, -2])
def test_file_only_requires_explicit_outputs(
    cluster: SimpleNamespace,
    tmp_path: pl.Path,
    amount: int,
) -> None:
    with pytest.raises(expected_exception=ValueError, match="explicit nonnegative parent outputs"):
        cluster.g_transaction.build_raw_tx(
            src_address="source",
            tx_name="manual",
            txins=[utxo()],
            txouts=[structs.TxOut(address="destination", amount=amount)],
            sub_transaction_files=["signed"],
            destination_dir=tmp_path,
        )


def test_file_only_requires_explicit_inputs(cluster: SimpleNamespace, tmp_path: pl.Path) -> None:
    with pytest.raises(expected_exception=ValueError, match="explicit parent spending inputs"):
        cluster.g_transaction.build_raw_tx(
            src_address="source",
            tx_name="manual",
            sub_transaction_files=["signed"],
            src_addr_utxos=[utxo()],
            destination_dir=tmp_path,
        )
    cluster.g_query.get_utxo.assert_not_called()


def test_file_only_script_inputs(cluster: SimpleNamespace, tmp_path: pl.Path) -> None:
    scripts = [structs.ScriptTxIn(txins=[utxo()], script_file="native.script")]
    result = cluster.g_transaction.build_raw_tx(
        src_address="unused",
        tx_name="manual_script",
        script_txins=scripts,
        fee=200_000,
        sub_transaction_files=["signed"],
        destination_dir=tmp_path,
    )
    assert result.txins == []
    assert result.script_txins == scripts
    assert result.txouts == []
    cluster.g_query.get_utxo.assert_not_called()


def test_file_only_and_typed_children_are_exclusive(
    cluster: SimpleNamespace,
    tmp_path: pl.Path,
) -> None:
    child = structs.SubTxRawOutput(
        txins=[utxo()],
        txouts=[],
        txouts_count=0,
        tx_files=structs.TxFiles(),
        out_file=tmp_path / "child",
        build_args=[],
    )
    with pytest.raises(expected_exception=ValueError, match="not both"):
        cluster.g_transaction.build_raw_tx(
            src_address="source",
            tx_name="mixed",
            txins=[utxo("parent")],
            sub_transactions=[structs.SignedSubTx(out_file="signed", tx_raw_output=child)],
            sub_transaction_files=["signed"],
            destination_dir=tmp_path,
        )
    cluster.cli.assert_not_called()


def test_empty_file_list_preserves_balancing(cluster: SimpleNamespace, tmp_path: pl.Path) -> None:
    cluster.g_query.get_utxo.return_value = [utxo()]
    amount = 1_000_000
    fee = 200_000
    result = cluster.g_transaction.build_raw_tx(
        src_address="source",
        tx_name="normal",
        fee=fee,
        txouts=[structs.TxOut(address="destination", amount=amount)],
        sub_transaction_files=[],
        destination_dir=tmp_path,
    )
    assert result.txouts == [
        structs.TxOut(address="destination", amount=amount),
        structs.TxOut(address="source", amount=utxo().amount - amount - fee),
    ]
    cluster.g_query.get_utxo.assert_called_once_with(address="source")


def test_batch_input_overlap(cluster: SimpleNamespace, tmp_path: pl.Path) -> None:
    child = structs.SubTxRawOutput(
        txins=[utxo()],
        txouts=[],
        txouts_count=0,
        tx_files=structs.TxFiles(),
        out_file=tmp_path / "child",
        build_args=[],
    )
    with pytest.raises(expected_exception=ValueError, match="same input"):
        txtools.collect_data_for_build(
            clusterlib_obj=cluster,
            src_address="source",
            txins=[utxo()],
            sub_transactions=[structs.SignedSubTx(out_file="signed", tx_raw_output=child)],
        )


def test_real_cli_pipeline(cluster: SimpleNamespace, tmp_path: pl.Path) -> None:
    binary = shutil.which("cardano-cli")
    if binary is None:
        pytest.skip("cardano-cli not installed")
    probe = subprocess.run(
        args=[binary, "dijkstra", "sub-transaction", "--help"], capture_output=True, check=False
    )
    if probe.returncode:
        pytest.skip("CLI does not support Dijkstra sub-transactions")

    def cli(args: list[str]) -> structs.CLIOut:
        proc = subprocess.run(args=[binary, "dijkstra", *args], capture_output=True, check=False)
        if proc.returncode:
            raise exceptions.CLIError(proc.stderr.decode())
        return structs.CLIOut(stdout=proc.stdout, stderr=proc.stderr)

    cluster.cli = cli
    keys = []
    for index in range(2):
        key = tmp_path / f"key{index}.skey"
        cli(
            [
                "address",
                "key-gen",
                "--verification-key-file",
                str(key.with_suffix(".vkey")),
                "--signing-key-file",
                str(key),
            ]
        )
        keys.append(key)
    children = []
    for index in range(2):
        body = cluster.g_sub_transaction.build_raw_tx_bare(
            out_file=tmp_path / f"child{index}.body",
            txins=[utxo(str(index) * 64)],
            out_canonical_cbor=True,
        )
        signed = cluster.g_sub_transaction.sign_tx(
            sub_tx_file=body.out_file,
            tx_name=f"child{index}",
            signing_key_files=keys if index else (),
            destination_dir=tmp_path,
        )
        assert cluster.g_sub_transaction.get_txid(
            sub_tx_file=body.out_file
        ) == cluster.g_sub_transaction.get_txid(signed_sub_tx_file=signed)
        assert json.loads(signed.read_text())["type"] == "Witnessed SubTx DijkstraEra"
        children.append(signed)
    parent = cluster.g_transaction.build_raw_tx(
        src_address="unused",
        tx_name="parent",
        txouts=[],
        tx_files=structs.TxFiles(),
        fee=200_000,
        txins=[utxo("b" * 64)],
        sub_transaction_files=children,
        destination_dir=tmp_path,
    )
    assert parent.out_file.exists()
    signed_parent = cluster.g_transaction.sign_tx(
        tx_body_file=parent.out_file,
        tx_name="parent",
        signing_key_files=keys,
        destination_dir=tmp_path,
    )
    for child in children:
        child_cbor = json.loads(child.read_text())["cborHex"]
        assert child_cbor in json.loads(signed_parent.read_text())["cborHex"]
    with pytest.raises(expected_exception=exceptions.CLIError, match="sub-transaction with id"):
        cluster.g_transaction.build_raw_tx_bare(
            out_file=tmp_path / "duplicate.body",
            txouts=[],
            tx_files=structs.TxFiles(),
            fee=200_000,
            txins=[utxo()],
            signed_sub_tx_files=[children[0], children[0]],
        )
    with pytest.raises(exceptions.CLIError):
        cluster.g_transaction.build_raw_tx_bare(
            out_file=tmp_path / "unsigned.body",
            txouts=[],
            tx_files=structs.TxFiles(),
            fee=200_000,
            txins=[utxo()],
            signed_sub_tx_files=[body.out_file],
        )


@pytest.mark.parametrize(argnames="residual", argvalues=[-2_000_000, 0, 2_000_000])
def test_batch_change(cluster: SimpleNamespace, tmp_path: pl.Path, residual: int) -> None:
    child = structs.SubTxRawOutput(
        txins=[utxo()],
        txouts=[structs.TxOut(address="destination", amount=10_000_000 - residual)],
        txouts_count=1,
        tx_files=structs.TxFiles(),
        out_file=tmp_path / "child",
        build_args=[],
    )
    result = txtools.collect_data_for_build(
        clusterlib_obj=cluster,
        src_address="source",
        txins=[utxo("b" * 64)],
        deposit=0,
        fee=200_000,
        sub_transactions=[structs.SignedSubTx(out_file="signed", tx_raw_output=child)],
    )
    assert sum(o.amount for o in result.txouts) == 10_000_000 + residual - 200_000


@pytest.mark.parametrize(argnames="residual", argvalues=[-2, 2])
def test_batch_token_change(cluster: SimpleNamespace, tmp_path: pl.Path, residual: int) -> None:
    child = structs.SubTxRawOutput(
        txins=[utxo(), utxo(amount=5, coin="token")],
        txouts=[
            structs.TxOut(address="destination", amount=10_000_000),
            structs.TxOut(address="destination", amount=5 - residual, coin="token"),
        ],
        txouts_count=1,
        tx_files=structs.TxFiles(),
        out_file=tmp_path / "child",
        build_args=[],
    )
    result = cluster.g_transaction.build_raw_tx(
        src_address="source",
        tx_name="tokens",
        fee=200_000,
        deposit=0,
        destination_dir=tmp_path,
        txins=[utxo("b" * 64), utxo(txhash="b" * 64, amount=5, coin="token")],
        sub_transactions=[structs.SignedSubTx(out_file="signed", tx_raw_output=child)],
    )
    assert sum(o.amount for o in result.txouts if o.coin == "token") == 5 + residual
    assert "--mint" not in result.build_args


def test_query_child_script_collateral_return(cluster: SimpleNamespace, tmp_path: pl.Path) -> None:
    output = structs.TxRawOutput(
        txins=[utxo()],
        txouts=[],
        txouts_count=0,
        tx_files=structs.TxFiles(),
        out_file=tmp_path / "body",
        fee=200_000,
        build_args=[],
        return_collateral_txouts=[structs.TxOut(address="source", amount=1_000_000)],
    )
    query = query_group.QueryGroup(cluster)
    with (
        mock.patch.object(target=query, attribute="query_cli", return_value="{}") as cli,
        mock.patch.object(
            target=cluster.g_transaction, attribute="get_txid", return_value="parent"
        ),
    ):
        assert query.get_utxo(tx_raw_output=output) == []
        assert "parent#0" in cli.call_args.args[0]


def test_insufficient_batch_funds(cluster: SimpleNamespace, tmp_path: pl.Path) -> None:
    child = structs.SubTxRawOutput(
        txins=[utxo()],
        txouts=[structs.TxOut(address="destination", amount=30_000_000)],
        txouts_count=1,
        tx_files=structs.TxFiles(),
        out_file=tmp_path / "child",
        build_args=[],
    )
    with pytest.raises(expected_exception=ValueError, match="Insufficient batch funds"):
        txtools.collect_data_for_build(
            clusterlib_obj=cluster,
            src_address="source",
            txins=[utxo("b" * 64)],
            deposit=0,
            fee=200_000,
            sub_transactions=[structs.SignedSubTx(out_file="signed", tx_raw_output=child)],
        )


def test_reference_and_collateral_selection(cluster: SimpleNamespace, tmp_path: pl.Path) -> None:
    reference = utxo("r" * 64)
    collateral = utxo("c" * 64)
    funding = utxo("f" * 64)
    child = structs.SubTxRawOutput(
        txins=[utxo()],
        txouts=[structs.TxOut(address="destination", amount=10_000_000)],
        txouts_count=1,
        tx_files=structs.TxFiles(),
        out_file=tmp_path / "child",
        build_args=[],
        combined_reference_txins=[reference],
    )
    result = txtools.collect_data_for_build(
        clusterlib_obj=cluster,
        src_address="source",
        deposit=0,
        fee=200_000,
        src_addr_utxos=[utxo(), reference, collateral, funding],
        reserved_txins=[collateral],
        sub_transactions=[structs.SignedSubTx(out_file="signed", tx_raw_output=child)],
    )
    assert result.txins == [funding]


@pytest.mark.parametrize(
    argnames="purpose",
    argvalues=["spending", "mint", "certificate", "proposal", "withdrawal", "vote"],
)
def test_v4_reference_witnesses(purpose: str) -> None:
    records = {
        "script_txins": [],
        "mint": [],
        "complex_certs": [],
        "complex_proposals": [],
        "script_withdrawals": [],
        "script_votes": [],
    }
    name, record = {
        "spending": ("script_txins", structs.ScriptTxIn([utxo()])),
        "mint": (
            "mint",
            structs.Mint(
                txouts=[structs.TxOut(address="", amount=1, coin="token")], policyid="policy"
            ),
        ),
        "certificate": ("complex_certs", structs.ComplexCert("cert")),
        "proposal": ("complex_proposals", structs.ComplexProposal("proposal")),
        "withdrawal": (
            "script_withdrawals",
            structs.ScriptWithdrawal(structs.TxOut(address="stake", amount=1)),
        ),
        "vote": ("script_votes", structs.ScriptVote("vote")),
    }[purpose]
    records[name] = [
        dataclasses.replace(
            record,
            reference_txin=utxo("reference"),
            reference_type=consts.ScriptTypes.PLUTUS_V4,
            redeemer_value="0",
            execution_units=(0, 0),
        )
    ]
    args = txtools._get_script_args(**records, for_sub_transaction=True)
    assert f"--{purpose}-plutus-script-v4" in args
    assert "--tx-in-collateral" not in args


def test_fee_and_send_forward_children(cluster: SimpleNamespace, tmp_path: pl.Path) -> None:
    expected_fee = 200_000
    reference_size = 42
    child = structs.SubTxRawOutput(
        txins=[utxo()],
        txouts=[],
        txouts_count=0,
        tx_files=structs.TxFiles(),
        out_file=tmp_path / "child",
        build_args=[],
    )
    children = [structs.SignedSubTx(out_file="signed", tx_raw_output=child)]
    collateral = [utxo("collateral")]
    tx = structs.TxRawOutput(
        txins=[utxo("parent")],
        txouts=[],
        txouts_count=0,
        tx_files=structs.TxFiles(),
        out_file=tmp_path / "parent",
        fee=1,
        build_args=[],
    )
    group = cluster.g_transaction
    with mock.patch.object(target=group, attribute="build_raw_tx", return_value=tx) as build:
        with mock.patch.object(
            target=group, attribute="estimate_fee", return_value=200_000
        ) as estimate:
            assert (
                group.calculate_tx_fee(
                    src_address="source",
                    tx_name="fee",
                    sub_transactions=children,
                    collateral_txins=collateral,
                )
                == expected_fee
            )
            assert build.call_args.kwargs["sub_transactions"] == children
            assert estimate.call_args.kwargs["witness_count"] == 0
        with (
            mock.patch.object(target=group, attribute="sign_tx", return_value=tmp_path / "signed"),
            mock.patch.object(target=group, attribute="submit_tx") as submit,
            mock.patch.object(
                target=group, attribute="calculate_tx_fee", return_value=expected_fee
            ) as fee,
        ):
            group.send_tx(
                src_address="source",
                tx_name="send",
                txins=tx.txins,
                sub_transactions=children,
                collateral_txins=collateral,
                reference_script_size=reference_size,
            )
            assert fee.call_args.kwargs["reference_script_size"] == reference_size
            assert build.call_args.kwargs["sub_transactions"] == children
            assert submit.call_args.kwargs["txins"] == tx.txins
