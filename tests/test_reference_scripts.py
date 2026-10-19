import dataclasses
import pathlib

import pytest

from cardano_clusterlib import consts
from cardano_clusterlib import structs
from cardano_clusterlib import txtools


class TestGovernanceReferenceScripts:
    @pytest.mark.parametrize(
        ("purpose", "record"),
        [
            ("proposal", structs.ComplexProposal(proposal_file="proposal.json")),
            ("vote", structs.ScriptVote(vote_file="vote.json")),
        ],
    )
    @pytest.mark.parametrize(
        ("script_type", "version"),
        [("", "v3"), (consts.ScriptTypes.PLUTUS_V3, "v3"), (consts.ScriptTypes.PLUTUS_V4, "v4")],
    )
    @pytest.mark.parametrize("redeemer", ["file", "cbor_file", "value"])
    @pytest.mark.parametrize("with_execution_units", [False, True])
    def test_reference_script_args(
        self,
        purpose: str,
        record: structs.ComplexProposal | structs.ScriptVote,
        script_type: str,
        version: str,
        redeemer: str,
        with_execution_units: bool,
    ) -> None:
        reference = structs.UTXOData(utxo_hash="reference", utxo_ix=1, amount=0, address="")
        collateral = structs.UTXOData(utxo_hash="collateral", utxo_ix=2, amount=0, address="")
        redeemer_value = "42" if redeemer == "value" else pathlib.Path("redeemer")
        script = dataclasses.replace(
            record,
            reference_txin=reference,
            reference_type=script_type,
            collaterals=[collateral],
            execution_units=(100, 200),
            **{f"redeemer_{redeemer}": redeemer_value},
        )
        args = txtools._get_script_args(
            script_txins=(),
            mint=(),
            complex_certs=(),
            complex_proposals=[script] if purpose == "proposal" else (),
            script_withdrawals=(),
            script_votes=[script] if purpose == "vote" else (),
            with_execution_units=with_execution_units,
        )
        expected = [
            f"--{purpose}-file",
            f"{purpose}.json",
            f"--{purpose}-tx-in-reference",
            "reference#1",
            f"--{purpose}-plutus-script-{version}",
        ]
        if with_execution_units:
            expected.extend([f"--{purpose}-reference-tx-in-execution-units", "(100,200)"])
        redeemer_arg = redeemer.replace("_", "-")
        expected.extend(
            [
                f"--{purpose}-reference-tx-in-redeemer-{redeemer_arg}",
                str(redeemer_value),
                "--tx-in-collateral",
                "collateral#2",
            ]
        )
        assert args == expected

    def test_script_file_args_unchanged(self) -> None:
        args = txtools._get_script_args(
            script_txins=(),
            mint=(),
            complex_certs=(),
            complex_proposals=[
                structs.ComplexProposal(
                    "proposal.json", script_file="proposal.plutus", redeemer_value="1"
                )
            ],
            script_withdrawals=(),
            script_votes=[
                structs.ScriptVote("vote.json", script_file="vote.plutus", redeemer_value="2")
            ],
        )
        assert args == [
            "--proposal-file",
            "proposal.json",
            "--proposal-script-file",
            "proposal.plutus",
            "--proposal-redeemer-value",
            "1",
            "--vote-file",
            "vote.json",
            "--vote-script-file",
            "vote.plutus",
            "--vote-redeemer-value",
            "2",
        ]

    def test_reference_inputs(self) -> None:
        references = [
            structs.UTXOData(utxo_hash="reference", utxo_ix=ix, amount=0, address="")
            for ix in range(3)
        ]
        combined = txtools._get_reference_txins(
            readonly_reference_txins=[references[0]],
            script_txins=(),
            mint=(),
            complex_certs=(),
            script_withdrawals=(),
            complex_proposals=[
                structs.ComplexProposal("proposal.json", reference_txin=references[1]),
                structs.ComplexProposal("plain_proposal.json"),
            ],
            script_votes=[
                structs.ScriptVote("vote.json", reference_txin=references[2]),
                structs.ScriptVote("plain_vote.json"),
            ],
        )
        assert combined == references
