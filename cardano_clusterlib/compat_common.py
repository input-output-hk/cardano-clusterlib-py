"""Generic reusable classes for cardano-cli `compatible` commands."""

import pathlib as pl
from typing import TYPE_CHECKING

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import consts
from cardano_clusterlib import exceptions
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
        return f"<StakeAddressGroup base={self._base}>"


class StakePoolGroup:
    """Generic stake-pool group for all compatible eras."""

    def __init__(self, clusterlib_obj: "ClusterLib", era: str) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base = ("cardano-cli", "compatible", era, "stake-pool")

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


class GovernanceActionGroup:
    """Governance action subcommands for compatible eras."""

    def __init__(self, clusterlib_obj: "ClusterLib", era: str) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base = ("cardano-cli", "compatible", era, "governance", "action")

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


class GovernanceGroup:
    """Generic governance group for all compatible eras."""

    def __init__(self, clusterlib_obj: "ClusterLib", era: str) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base = ("cardano-cli", "compatible", era, "governance")
        self.action = GovernanceActionGroup(clusterlib_obj, era)

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


class TransactionGroup:
    """Compatible transaction commands for legacy eras (Alonzo / Mary / Babbage).
    """

    def __init__(self, clusterlib_obj: "ClusterLib", era: str) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base = ("cardano-cli", "compatible", era, "transaction")
        self._min_fee = self._clusterlib_obj.genesis["protocolParams"]["minFeeB"]


    def gen_signed_tx_raw(
        self,
        *,
        name: str,
        cli_args: itp.UnpackableSequence,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Run `... transaction signed-transaction` with pre-built CLI args.
        """
        destination_dir_path = pl.Path(destination_dir).expanduser()
        out_file = destination_dir_path / f"{name}_signed.tx"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        cmd = [
            *self._base,
            "signed-transaction",
            *cli_args,
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)
        helpers._check_outfiles(out_file)

        return out_file


    def _select_ada_utxos_naive(
        self,
        *,
        src_address: str,
        amount_required: int,
        fee: int,
    ) -> list[structs.UTXOData]:
        """Select simple ADA UTxOs from `src_address` to cover amount + fee.

        Rules:
          * Only pure ADA UTxOs (no datum, no inline datum, no reference script).

        """
        utxos = self._clusterlib_obj.g_query.get_utxo(
            address=src_address,
            coins=[consts.DEFAULT_COIN],
        )

        usable_utxos = [
            u
            for u in utxos
            if not u.datum_hash and not u.inline_datum_hash and not u.reference_script
        ]

        if not usable_utxos:
            message = f"No usable ADA UTxOs for address {src_address}."
            raise exceptions.CLIError(message)

        target = amount_required + fee
        if target <= 0:
            # At minimum we must cover the fee
            target = fee

        sorted_utxos = sorted(usable_utxos, key=lambda u: u.amount)

        selected: list[structs.UTXOData] = []
        running_total = 0

        for utxo in sorted_utxos:
            selected.append(utxo)
            running_total += utxo.amount
            if running_total >= target:
                break

        if running_total < target:
            message = (
                f"Insufficient ADA for transaction: required {target}, available {running_total}."
            )
            raise exceptions.CLIError(message)

        return selected


    def gen_signed_tx(
        self,
        *,
        name: str,
        src_address: str,
        txouts: list[structs.TxOut],
        tx_files: structs.TxFiles,
        fee: int,
        destination_dir: itp.FileType = ".",
    ) -> structs.TxRawOutput:
        """Generate a simple signed transaction for compatible eras.
        """
        destination_dir_path = pl.Path(destination_dir).expanduser()
        out_file = destination_dir_path / f"{name}_signed.tx"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        # 1) Compute net deposit from certificates using the main (non-compatible) Tx group
        deposit = 0
        if tx_files.certificate_files:
            deposit = self._clusterlib_obj.g_transaction.get_tx_deposit(tx_files=tx_files)

        # 2) Sum ADA outputs (ignore non-ADA coins for now)
        ada_outputs = [t for t in txouts if t.coin == consts.DEFAULT_COIN]
        total_out = sum(t.amount for t in ada_outputs)
        amount_required = total_out + deposit

        # 3) Select ADA UTxOs from the source address
        selected_utxos = self._select_ada_utxos_naive(
            src_address=src_address,
            amount_required=amount_required,
            fee=fee,
        )
        total_in = sum(u.amount for u in selected_utxos)

        # 4) Compute change (if any) back to the source address
        change_amount = total_in - amount_required - fee
        change_txouts: list[structs.TxOut] = []
        if change_amount > 0:
            change_txouts.append(
                structs.TxOut(
                    address=src_address,
                    amount=change_amount,
                    coin=consts.DEFAULT_COIN,
                )
            )

        final_txouts = [*txouts, *change_txouts]

        # 5) Build `--tx-in` and `--tx-out` CLI args
        txin_args: list[str] = []
        for utxo in selected_utxos:
            txin_args.extend(
                [
                    "--tx-in",
                    f"{utxo.utxo_hash}#{utxo.utxo_ix}",
                ]
            )

        # Reuse existing joining logic so `txouts_count` etc. are consistent
        txout_args, processed_txouts, txouts_count = txtools._process_txouts(
            txouts=final_txouts,
            join_txouts=True,
        )

        # Certificates (if any)
        cert_args = helpers._prepend_flag("--certificate-file", tx_files.certificate_files)

        # Signing keys
        skey_args = helpers._prepend_flag("--signing-key-file", tx_files.signing_key_files)

        # 6) Compose CLI args for `signed-transaction`
        cli_args: list[str] = [
            *txin_args,
            *txout_args,
            *cert_args,
            *skey_args,
            "--fee",
            str(fee),
            *self._clusterlib_obj.magic_args,
        ]

        # 7) Run the compat CLI and produce the signed tx file
        cmd = [
            *self._base,
            "signed-transaction",
            *cli_args,
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)
        helpers._check_outfiles(out_file)

        # 8) Return a TxRawOutput describing what we just did
        return structs.TxRawOutput(
            txins=selected_utxos,
            txouts=processed_txouts,
            txouts_count=txouts_count,
            tx_files=tx_files,
            out_file=out_file,
            fee=fee,
            build_args=cmd,
            era=self._clusterlib_obj.era_in_use,
        )

    def __repr__(self) -> str:
        return f"<TransactionGroup base={self._base}>"
