"""Build and sign Dijkstra sub-transactions independently of their enclosing transaction."""

import itertools
import pathlib as pl

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import consts
from cardano_clusterlib import exceptions
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
from cardano_clusterlib import txtools
from cardano_clusterlib import types as itp


class SubTransactionGroup:
    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj
        self._supported_era: str | None = None

    def _check_supported(self) -> None:
        """Probe the selected CLI era, including the actual meaning of 'latest'."""
        era = self._clusterlib_obj.command_era
        if self._supported_era == era:
            return

        try:
            self._clusterlib_obj.cli(["sub-transaction", "--help"])
        except exceptions.CLIError as exc:
            msg = f"Sub-transactions are unavailable in command era '{era}' with this CLI."
            raise exceptions.CLIError(msg) from exc

        self._supported_era = era

    def build_raw_tx_bare(
        self,
        out_file: itp.FileType,
        txouts: structs.OptionalTxOuts = (),
        tx_files: structs.TxFiles | None = None,
        txins: structs.OptionalUTXOData = (),
        readonly_reference_txins: structs.OptionalUTXOData = (),
        script_txins: structs.OptionalScriptTxIn = (),
        mint: structs.OptionalMint = (),
        complex_certs: structs.OptionalScriptCerts = (),
        complex_proposals: structs.OptionalScriptProposals = (),
        withdrawals: structs.OptionalTxOuts = (),
        script_withdrawals: structs.OptionalScriptWithdrawals = (),
        script_votes: structs.OptionalScriptVotes = (),
        direct_deposits: structs.OptionalTxOuts = (),
        guards: list[structs.TxGuard] | tuple[()] = (),
        top_level_guards: list[structs.RequiredTopLevelGuard] | tuple[()] = (),
        invalid_before: int | None = None,
        invalid_hereafter: int | None = None,
        current_treasury_value: int | None = None,
        treasury_donation: int | None = None,
        protocol_params_file: itp.FileType = "",
        out_canonical_cbor: bool = False,
        join_txouts: bool = True,
    ) -> structs.SubTxRawOutput:
        """Build with explicit inputs/outputs; no balancing or signing is performed.

        Uses the same transaction records as the parent builders, except collateral is
        forbidden and reference scripts must explicitly select native scripts or Plutus V4.
        Script files are checked by the CLI. Amounts must be explicit except withdrawals,
        where -1 resolves the current rewards. Direct deposits use TxOut stake addresses
        and positive lovelace amounts. Guards and top-level requirements retain list order.
        Supply protocol_params_file for offline Plutus building; otherwise protocol
        parameters are obtained from the node when script data requires them.
        Canonicalization, if requested, happens before signing.
        """
        self._check_supported()

        out_file = pl.Path(out_file).expanduser()
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        tx_files = tx_files or structs.TxFiles()

        if any(o.amount < 0 for o in txouts):
            msg = "Sub-transaction outputs must have explicit nonnegative amounts."
            raise ValueError(msg)

        if any(o.coin != consts.DEFAULT_COIN or o.amount <= 0 for o in direct_deposits):
            msg = "Direct deposits require positive lovelace amounts."
            raise ValueError(msg)

        withdrawals, script_withdrawals, __ = txtools._get_withdrawals(
            clusterlib_obj=self._clusterlib_obj,
            withdrawals=withdrawals,
            script_withdrawals=script_withdrawals,
        )

        script_args = txtools._get_script_args(
            script_txins=script_txins,
            mint=mint,
            complex_certs=complex_certs,
            complex_proposals=complex_proposals,
            script_withdrawals=script_withdrawals,
            script_votes=script_votes,
            for_sub_transaction=True,
        )

        guard_args = list(
            itertools.chain.from_iterable(
                txtools._get_guard_args(g) for g in (*guards, *top_level_guards)
            )
        )

        txout_args, processed_txouts, txouts_count = txtools._process_txouts(
            txouts=list(txouts),
            join_txouts=join_txouts,
        )

        misc_args: list[str] = []

        for flag, val in (
            ("--invalid-before", invalid_before),
            ("--invalid-hereafter", invalid_hereafter),
            ("--current-treasury-value", current_treasury_value),
            ("--treasury-donation", treasury_donation),
        ):
            if val is not None:
                misc_args.extend([flag, str(val)])

        if protocol_params_file:
            misc_args.extend(["--protocol-params-file", str(protocol_params_file)])
        elif (
            any("-redeemer-" in a or "-datum-" in a for a in script_args)
            or any(a.startswith("--guard-redeemer-") for a in guard_args)
            or any("datum-embed-" in a for a in txout_args)
        ):
            self._clusterlib_obj.create_pparams_file()
            misc_args.extend(["--protocol-params-file", str(self._clusterlib_obj.pparams_file)])

        minted = [f"{o.amount} {o.coin}" for m in mint for o in m.txouts]
        if minted:
            misc_args.extend(["--mint", "+".join(minted)])

        if out_canonical_cbor:
            misc_args.append("--out-canonical-cbor")

        if tx_files.metadata_json_files and tx_files.metadata_json_detailed_schema:
            misc_args.append("--json-metadata-detailed-schema")

        cli_args = [
            "sub-transaction",
            "build-raw",
            *script_args,
            *helpers._prepend_flag(
                flag="--tx-in",
                contents=txtools._get_txin_strings(txins=txins, script_txins=script_txins),
            ),
            *helpers._prepend_flag(
                flag="--read-only-tx-in-reference",
                contents=[f"{t.utxo_hash}#{t.utxo_ix}" for t in readonly_reference_txins],
            ),
            *txout_args,
            *helpers._prepend_flag(flag="--certificate-file", contents=tx_files.certificate_files),
            *helpers._prepend_flag(flag="--proposal-file", contents=tx_files.proposal_files),
            *helpers._prepend_flag(flag="--vote-file", contents=tx_files.vote_files),
            *helpers._prepend_flag(
                flag="--auxiliary-script-file", contents=tx_files.auxiliary_script_files
            ),
            *helpers._prepend_flag(
                flag="--metadata-json-file", contents=tx_files.metadata_json_files
            ),
            *helpers._prepend_flag(
                flag="--metadata-cbor-file", contents=tx_files.metadata_cbor_files
            ),
            *helpers._prepend_flag(
                flag="--withdrawal", contents=[f"{o.address}+{o.amount}" for o in withdrawals]
            ),
            *helpers._prepend_flag(
                flag="--direct-deposit",
                contents=[f"{o.address}+{o.amount}" for o in direct_deposits],
            ),
            *guard_args,
            *misc_args,
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cli_args)
        helpers._check_outfiles(out_file)

        return structs.SubTxRawOutput(
            txins=list(txins),
            txouts=processed_txouts,
            txouts_count=txouts_count,
            tx_files=tx_files,
            out_file=out_file,
            build_args=cli_args,
            script_txins=script_txins,
            readonly_reference_txins=readonly_reference_txins,
            combined_reference_txins=txtools._get_reference_txins(
                readonly_reference_txins=readonly_reference_txins,
                script_txins=script_txins,
                mint=mint,
                complex_certs=complex_certs,
                script_withdrawals=script_withdrawals,
                complex_proposals=complex_proposals,
                script_votes=script_votes,
            ),
            mint=mint,
            complex_certs=complex_certs,
            complex_proposals=complex_proposals,
            withdrawals=withdrawals,
            script_withdrawals=script_withdrawals,
            script_votes=script_votes,
            direct_deposits=direct_deposits,
            guards=guards,
            top_level_guards=top_level_guards,
            invalid_before=invalid_before,
            invalid_hereafter=invalid_hereafter,
            current_treasury_value=current_treasury_value,
            treasury_donation=treasury_donation,
        )

    def sign_tx(
        self,
        sub_tx_file: itp.FileType,
        tx_name: str,
        signing_key_files: itp.OptionalFiles = (),
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Sign an unsigned sub-transaction with zero or more Shelley keys.

        This does not support incremental signing or Byron witnesses. Zero keys still
        produces the signed envelope required for embedding script-authorized children.
        """
        self._check_supported()

        out_file = pl.Path(destination_dir).expanduser() / f"{tx_name}_sub_tx.signed"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        self._clusterlib_obj.cli(
            [
                "sub-transaction",
                "sign",
                "--sub-tx-file",
                str(sub_tx_file),
                *helpers._prepend_flag(flag="--signing-key-file", contents=signing_key_files),
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def get_txid(
        self,
        sub_tx_file: itp.FileType = "",
        signed_sub_tx_file: itp.FileType = "",
    ) -> str:
        """Return the body ID of exactly one unsigned or signed sub-transaction."""
        if bool(sub_tx_file) == bool(signed_sub_tx_file):
            msg = "Specify exactly one of sub_tx_file and signed_sub_tx_file."
            raise ValueError(msg)

        self._check_supported()

        flag = "--sub-tx-file" if sub_tx_file else "--signed-sub-tx-file"

        return (
            self._clusterlib_obj.cli(
                [
                    "sub-transaction",
                    "txid",
                    flag,
                    str(sub_tx_file or signed_sub_tx_file),
                    "--output-text",
                ]
            )
            .stdout.decode("ascii")
            .strip()
        )
