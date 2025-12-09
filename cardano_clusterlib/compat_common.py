"""Generic reusable classes for cardano-cli `compatible` commands."""

import pathlib as pl
from typing import TYPE_CHECKING

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
from cardano_clusterlib import txtools
from cardano_clusterlib import types as itp

if TYPE_CHECKING:
    from cardano_clusterlib.clusterlib_klass import ClusterLib


class StakeAddressGroup:
    """Compatible stake-address commands for Alonzo / Mary / Babbage eras."""

    def __init__(self, clusterlib_obj: "ClusterLib", era: str) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base = ("cardano-cli", "compatible", era, "stake-address")
        self.era = era

    def _resolve_stake_key_args(
        self,
        *,
        stake_vkey: str = "",
        stake_vkey_file: itp.FileType | None = None,
        stake_key_hash: str = "",
        stake_script_file: itp.FileType | None = None,
        stake_address: str | None = None,
    ) -> list[str]:
        """Resolve stake key CLI args (compatible-era logic)."""
        if stake_vkey:
            return ["--stake-verification-key", stake_vkey]

        if stake_vkey_file:
            return ["--stake-verification-key-file", str(stake_vkey_file)]

        if stake_key_hash:
            return ["--stake-key-hash", stake_key_hash]

        if stake_script_file:
            return ["--stake-script-file", str(stake_script_file)]

        if stake_address:
            return ["--stake-address", stake_address]

        message = (
            "One of stake_vkey, stake_vkey_file, stake_key_hash, "
            "stake_script_file or stake_address must be provided."
        )
        raise ValueError(message)

    def gen_registration_cert(
        self,
        *,
        name: str,
        stake_vkey: str = "",
        stake_vkey_file: itp.FileType | None = None,
        stake_key_hash: str = "",
        stake_script_file: itp.FileType | None = None,
        stake_address: str | None = None,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a stake address registration certificate (compatible era)."""
        destination_dir_path = pl.Path(destination_dir).expanduser()
        out_file = destination_dir_path / f"{name}_stake_reg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        stake_args = self._resolve_stake_key_args(
            stake_vkey=stake_vkey,
            stake_vkey_file=stake_vkey_file,
            stake_key_hash=stake_key_hash,
            stake_script_file=stake_script_file,
            stake_address=stake_address,
        )

        cmd = [
            *self._base,
            "registration-certificate",
            *stake_args,
            *self._clusterlib_obj.magic_args,
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)
        helpers._check_outfiles(out_file)

        return out_file

    def gen_delegation_cert(
        self,
        *,
        name: str,
        stake_vkey: str = "",
        stake_vkey_file: itp.FileType | None = None,
        stake_key_hash: str = "",
        stake_script_file: itp.FileType | None = None,
        stake_address: str | None = None,
        stake_pool_vkey: str = "",
        cold_vkey_file: itp.FileType | None = None,
        stake_pool_id: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a stake delegation certificate (compatible era)."""
        destination_dir_path = pl.Path(destination_dir).expanduser()
        out_file = destination_dir_path / f"{name}_stake_deleg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        # Stake identification:
        stake_args = self._resolve_stake_key_args(
            stake_vkey=stake_vkey,
            stake_vkey_file=stake_vkey_file,
            stake_key_hash=stake_key_hash,
            stake_script_file=stake_script_file,
            stake_address=stake_address,
        )

        # Pool identification:
        if stake_pool_vkey:
            pool_args = ["--stake-pool-verification-key", stake_pool_vkey]
        elif cold_vkey_file:
            pool_args = ["--cold-verification-key-file", str(cold_vkey_file)]
        elif stake_pool_id:
            pool_args = ["--stake-pool-id", stake_pool_id]
        else:
            message = (
                "One of stake_pool_vkey, cold_vkey_file or stake_pool_id "
                "must be provided for delegation."
            )
            raise ValueError(message)

        cmd = [
            *self._base,
            "stake-delegation-certificate",
            *stake_args,
            *pool_args,
            *self._clusterlib_obj.magic_args,
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)
        helpers._check_outfiles(out_file)

        return out_file

    def __repr__(self) -> str:
        return f"<StakeAddressGroup era={self.era} base={self._base}>"


class StakePoolGroup:
    """Generic stake-pool group for all compatible eras."""

    def __init__(self, clusterlib_obj: "ClusterLib", era: str) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base = ("cardano-cli", "compatible", era, "stake-pool")
        self.era = era

    def gen_registration_cert(
        self,
        *,
        name: str,
        pool_params: structs.CompatPoolParams,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a compatible stake pool registration certificate."""
        pool_data = pool_params.pool_data

        destination_dir_path = pl.Path(destination_dir).expanduser()
        out_file = destination_dir_path / f"{name}_pool_reg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        metadata_args: list[str] = []
        if pool_data.pool_metadata_url and pool_data.pool_metadata_hash:
            metadata_args.extend(
                [
                    "--metadata-url",
                    str(pool_data.pool_metadata_url),
                    "--metadata-hash",
                    str(pool_data.pool_metadata_hash),
                ]
            )
            if pool_params.check_metadata_hash:
                metadata_args.append("--check-metadata-hash")

        relay_args: list[str] = []
        if pool_data.pool_relay_dns:
            relay_args.extend(["--single-host-pool-relay", pool_data.pool_relay_dns])

        if pool_data.pool_relay_ipv4:
            relay_args.extend(["--pool-relay-ipv4", pool_data.pool_relay_ipv4])

        if pool_params.relay_ipv6:
            relay_args.extend(["--pool-relay-ipv6", pool_params.relay_ipv6])

        if pool_data.pool_relay_port:
            relay_args.extend(["--pool-relay-port", str(pool_data.pool_relay_port)])

        if pool_params.multi_host_relay:
            relay_args.extend(["--multi-host-pool-relay", pool_params.multi_host_relay])

        # Reward account, default to first owner if not provided
        if pool_params.reward_account_vkey_file:
            reward_arg = [
                "--pool-reward-account-verification-key-file",
                str(pool_params.reward_account_vkey_file),
            ]
        else:
            default_owner = next(iter(pool_params.owner_stake_vkey_files))
            reward_arg = [
                "--pool-reward-account-verification-key-file",
                str(default_owner),
            ]

        cmd = [
            *self._base,
            "registration-certificate",
            "--pool-pledge",
            str(pool_data.pool_pledge),
            "--pool-cost",
            str(pool_data.pool_cost),
            "--pool-margin",
            str(pool_data.pool_margin),
            "--vrf-verification-key-file",
            str(pool_params.vrf_vkey_file),
            "--cold-verification-key-file",
            str(pool_params.cold_vkey_file),
            *reward_arg,
            *helpers._prepend_flag(
                "--pool-owner-stake-verification-key-file",
                pool_params.owner_stake_vkey_files,
            ),
            *self._clusterlib_obj.magic_args,
            "--out-file",
            str(out_file),
            *metadata_args,
            *relay_args,
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)
        helpers._check_outfiles(out_file)

        return out_file

    def gen_dereg_cert(
        self,
        *,
        name: str,
        params: structs.CompatPoolDeregParams,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a compatible stake pool deregistration certificate."""
        destination_dir_path = pl.Path(destination_dir).expanduser()
        out_file = destination_dir_path / f"{name}_pool_dereg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        cmd = [
            *self._base,
            "deregistration-certificate",
            "--cold-verification-key-file",
            str(params.cold_vkey_file),
            "--epoch",
            str(params.epoch),
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)
        helpers._check_outfiles(out_file)

        return out_file

    def __repr__(self) -> str:
        return f"<StakePoolGroup era={self.era} base={self._base}>"


class GovernanceActionGroup:
    """Governance action subcommands for compatible eras."""

    def __init__(self, clusterlib_obj: "ClusterLib", era: str) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base = ("cardano-cli", "compatible", era, "governance", "action")
        self.era = era

    def gen_pparams_update(
        self,
        *,
        name: str,
        epoch: int,
        genesis_vkey_file: itp.FileType,
        cli_args: itp.UnpackableSequence,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a protocol parameters update proposal for compatible eras."""
        destination_dir_path = pl.Path(destination_dir).expanduser()
        out_file = destination_dir_path / f"{name}_pparams_update.action"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        cmd = [
            *self._base,
            "create-protocol-parameters-update",
            *self._clusterlib_obj.magic_args,
            "--epoch",
            str(epoch),
            "--genesis-verification-key-file",
            str(genesis_vkey_file),
            *cli_args,
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)
        helpers._check_outfiles(out_file)

        return out_file

    def __repr__(self) -> str:
        return f"<GovernanceActionGroup era={self.era} base={self._base}>"


class GovernanceGroup:
    """Generic governance group for all compatible eras."""

    def __init__(self, clusterlib_obj: "ClusterLib", era: str) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base = ("cardano-cli", "compatible", era, "governance")
        self.action = GovernanceActionGroup(clusterlib_obj, era)
        self.era = era

    def _resolve_mir_direct_args(
        self,
        *,
        reserves: bool,
        treasury: bool,
        stake_address: str | None,
        reward: int | None,
    ) -> list[str] | None:
        """Resolve direct MIR args (no subcommand)."""
        if not reserves and not treasury:
            return None

        if reserves and treasury:
            msg = "Cannot specify both `reserves` and `treasury` in MIR direct mode."
            raise ValueError(msg)

        if not stake_address:
            msg = "`stake_address` is required in MIR direct mode."
            raise ValueError(msg)

        if reward is None:
            msg = "`reward` is required in MIR direct mode."
            raise ValueError(msg)

        pot_flag = "--reserves" if reserves else "--treasury"

        return [
            pot_flag,
            "--stake-address",
            stake_address,
            "--reward",
            str(reward),
        ]

    def _mir_stake_addresses_args(
        self,
        *,
        stake_address: str | None,
        reward: int | None,
        funds: str | None,
    ) -> list[str]:
        """Args for MIR `stake-addresses` subcommand."""
        if not stake_address:
            msg = "`stake_address` is required for MIR stake-addresses."
            raise ValueError(msg)

        if reward is None:
            msg = "`reward` is required for MIR stake-addresses."
            raise ValueError(msg)

        if funds not in ("reserves", "treasury"):
            msg = "`funds` must be either 'reserves' or 'treasury'."
            raise ValueError(msg)

        return [
            "stake-addresses",
            f"--{funds}",
            "--stake-address",
            stake_address,
            "--reward",
            str(reward),
        ]

    def _mir_transfer_to_treasury_args(
        self,
        *,
        transfer_amt: int | None,
    ) -> list[str]:
        if transfer_amt is None:
            msg = "`transfer_amt` is required for MIR transfer-to-treasury."
            raise ValueError(msg)

        return [
            "transfer-to-treasury",
            "--transfer",
            str(transfer_amt),
        ]

    def _mir_transfer_to_rewards_args(
        self,
        *,
        transfer_amt: int | None,
    ) -> list[str]:
        if transfer_amt is None:
            msg = "`transfer_amt` is required for MIR transfer-to-rewards."
            raise ValueError(msg)

        return [
            "transfer-to-rewards",
            "--transfer",
            str(transfer_amt),
        ]

    def _resolve_mir_subcommand_args(
        self,
        *,
        subcommand: str | None,
        stake_address: str | None,
        reward: int | None,
        transfer_amt: int | None,
        funds: str | None,
    ) -> list[str] | None:
        """Resolve MIR subcommand args."""
        if not subcommand:
            return None

        if subcommand == "stake-addresses":
            return self._mir_stake_addresses_args(
                stake_address=stake_address,
                reward=reward,
                funds=funds,
            )

        if subcommand == "transfer-to-treasury":
            return self._mir_transfer_to_treasury_args(
                transfer_amt=transfer_amt,
            )

        if subcommand == "transfer-to-rewards":
            return self._mir_transfer_to_rewards_args(
                transfer_amt=transfer_amt,
            )

        msg = f"Unknown MIR subcommand: {subcommand}"
        raise ValueError(msg)

    def gen_mir_cert(
        self,
        *,
        name: str,
        reserves: bool = False,
        treasury: bool = False,
        reward: int | None = None,
        stake_address: str | None = None,
        subcommand: str | None = None,
        transfer_amt: int | None = None,
        funds: str | None = None,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate MIR certificate for Babbage compatible eras."""
        destination_dir_path = pl.Path(destination_dir).expanduser()

        direct_args = self._resolve_mir_direct_args(
            reserves=reserves,
            treasury=treasury,
            stake_address=stake_address,
            reward=reward,
        )

        subcmd_args = self._resolve_mir_subcommand_args(
            subcommand=subcommand,
            stake_address=stake_address,
            reward=reward,
            transfer_amt=transfer_amt,
            funds=funds,
        )

        if direct_args and subcmd_args:
            msg = "Cannot mix MIR direct mode with MIR subcommand mode."
            raise ValueError(msg)

        if not direct_args and not subcmd_args:
            msg = "No MIR mode selected."
            raise ValueError(msg)

        final_args: list[str] = direct_args if direct_args is not None else subcmd_args  # type: ignore

        if direct_args:
            out_file = destination_dir_path / f"{name}_mir_direct.cert"
        elif subcommand == "stake-addresses":
            out_file = destination_dir_path / f"{name}_mir_stake.cert"
        elif subcommand == "transfer-to-treasury":
            out_file = destination_dir_path / f"{name}_mir_to_treasury.cert"
        else:
            out_file = destination_dir_path / f"{name}_mir_to_rewards.cert"

        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        cmd = [
            *self._base,
            "create-mir-certificate",
            *final_args,
            *self._clusterlib_obj.magic_args,
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)
        helpers._check_outfiles(out_file)

        return out_file

    def __repr__(self) -> str:
        return f"<GovernanceGroup era={self.era} base={self._base}>"


class TransactionGroup:
    """Compatible transaction commands for legacy eras (Alonzo / Mary / Babbage).

    This is a lightweight wrapper around:
    - txtools.collect_data_for_build  -> UTxO selection, balancing, deposits
    - `cardano-cli compatible <era> transaction signed-transaction`

    It is intentionally simpler than the Conway TransactionGroup:
    - No Plutus scripts
    - No minting or burning
    - No withdrawals
    - No collateral
    - No reference inputs

    Main use for compatible eras:
    - simple ADA transfers
    - stake key registration or deregistration
    - pool registration or deregistration
    - governance certificates (MIR, genesis delegation, protocol parameter updates)
    """

    def __init__(self, clusterlib_obj: "ClusterLib", era: str) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base = ("cardano-cli", "compatible", era, "transaction")
        self.era = era

    def gen_signed_tx_bare(
        self,
        *,
        name: str,
        txins: structs.OptionalUTXOData,
        txouts: list[structs.TxOut],
        tx_files: structs.TxFiles,
        fee: int,
        destination_dir: itp.FileType = ".",
        join_txouts: bool = True,
    ) -> pl.Path:
        """Generate a simple signed transaction using pre-balanced inputs and outputs.

        Assumptions:
        - `txins` already contain selected UTxOs
        - `txouts` are already balanced (including change and deposits)
        - `fee` is already decided
        """
        destination_dir_path = pl.Path(destination_dir).expanduser()
        out_file = destination_dir_path / f"{name}_tx.signed"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        txout_args, processed_txouts, __ = txtools._process_txouts(
            txouts=list(txouts),
            join_txouts=join_txouts,
        )

        txin_strings = txtools._get_txin_strings(
            txins=txins,
            script_txins=(),
        )

        cmd = [
            *self._base,
            "signed-transaction",
            *helpers._prepend_flag("--tx-in", txin_strings),
            *txout_args,
            *helpers._prepend_flag("--certificate-file", tx_files.certificate_files),
            *helpers._prepend_flag("--signing-key-file", tx_files.signing_key_files),
            *self._clusterlib_obj.magic_args,
            "--fee",
            str(fee),
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)
        helpers._check_outfiles(out_file)

        _ = processed_txouts
        return out_file

    def gen_signed_tx(
        self,
        *,
        name: str,
        src_address: str,
        txouts: structs.OptionalTxOuts,
        tx_files: structs.TxFiles,
        fee: int,
        txins: structs.OptionalUTXOData = (),
        deposit: int | None = None,
        treasury_donation: int | None = None,
        src_addr_utxos: list[structs.UTXOData] | None = None,
        destination_dir: itp.FileType = ".",
        join_txouts: bool = True,
        script_valid: bool = True,
    ) -> structs.TxRawOutput:
        """High-level helper to build and sign a compatible transaction.

        It reuses txtools.collect_data_for_build to:
        - select UTxOs (if `txins` not provided)
        - compute deposits (stake key, pool, governance)
        - balance outputs and change

        Then it calls gen_signed_tx_bare to run `signed-transaction` and wraps
        everything into TxRawOutput for tests.
        """
        destination_dir_path = pl.Path(destination_dir).expanduser()
        effective_tx_files = tx_files or structs.TxFiles()

        collected = txtools.collect_data_for_build(
            clusterlib_obj=self._clusterlib_obj,
            src_address=src_address,
            txins=txins,
            txouts=list(txouts),
            script_txins=(),
            mint=(),
            tx_files=effective_tx_files,
            complex_certs=(),
            complex_proposals=(),
            fee=fee,
            withdrawals=(),
            script_withdrawals=(),
            deposit=deposit,
            treasury_donation=treasury_donation or 0,
            src_addr_utxos=src_addr_utxos,
            skip_asset_balancing=False,
        )

        signed_tx_file = self.gen_signed_tx_bare(
            name=name,
            txins=collected.txins,
            txouts=collected.txouts,
            tx_files=effective_tx_files,
            fee=fee,
            destination_dir=destination_dir_path,
            join_txouts=join_txouts,
        )

        txout_args, processed_txouts, txouts_count = txtools._process_txouts(
            txouts=collected.txouts,
            join_txouts=join_txouts,
        )
        txin_strings = txtools._get_txin_strings(
            txins=collected.txins,
            script_txins=(),
        )

        build_args = [
            *self._base,
            "signed-transaction",
            *helpers._prepend_flag("--tx-in", txin_strings),
            *txout_args,
            *helpers._prepend_flag("--certificate-file", effective_tx_files.certificate_files),
            *helpers._prepend_flag("--signing-key-file", effective_tx_files.signing_key_files),
            *self._clusterlib_obj.magic_args,
            "--fee",
            str(fee),
            "--out-file",
            str(signed_tx_file),
        ]

        return structs.TxRawOutput(
            txins=list(collected.txins),
            txouts=processed_txouts,
            txouts_count=txouts_count,
            tx_files=effective_tx_files,
            out_file=signed_tx_file,
            fee=fee,
            build_args=build_args,
            era=self._clusterlib_obj.era_in_use,
            script_txins=(),
            script_withdrawals=(),
            script_votes=(),
            complex_certs=(),
            complex_proposals=(),
            mint=(),
            invalid_hereafter=None,
            invalid_before=None,
            current_treasury_value=None,
            treasury_donation=treasury_donation,
            withdrawals=(),
            change_address=src_address,
            return_collateral_txouts=(),
            total_collateral_amount=None,
            readonly_reference_txins=(),
            script_valid=script_valid,
            required_signers=effective_tx_files.signing_key_files,
            required_signer_hashes=(),
            combined_reference_txins=(),
        )

    def __repr__(self) -> str:
        return f"<TransactionGroup era={self.era} base={self._base}>"
