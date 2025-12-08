"""Generic reusable classes for cardano-cli `compatible` commands."""

import pathlib as pl
from typing import TYPE_CHECKING

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import consts
from cardano_clusterlib import exceptions
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
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
    """Generic transaction group for all compatible eras."""

    def __init__(self, clusterlib_obj: "ClusterLib", era: str) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base = ("cardano-cli", "compatible", era, "transaction")

    def gen_signed_tx(
        self,
        *,
        name: str,
        cli_args: itp.UnpackableSequence,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a simple signed transaction file (compatible-era)."""
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

    def create_signed_tx(
        self,
        *,
        name: str,
        src_address: str,
        txouts: list[structs.TxOut],
        signing_key_files: itp.OptionalFiles,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Create, balance, and sign a simple compatible-era transaction.

        Constraints:
        * ADA only (no multi-asset, no scripts, no metadata)
        * simple UTxO selection and balancing
        """
        # 1 Query UTxOs for the source address
        utxos = self._clusterlib_obj.g_query.get_utxo(address=src_address)

        ada_utxos = [
            u
            for u in utxos
            if u.coin == consts.DEFAULT_COIN and not u.datum_hash and not u.inline_datum_hash
        ]

        if not ada_utxos:
            message = f"No usable ADA UTxOs for {src_address}"
            raise exceptions.CLIError(message)

        # Required ADA amount (sum of requested outputs)
        amount_required = sum(t.amount for t in txouts)

        # 3 Simple fee buffers
        min_fee_b = self._clusterlib_obj.genesis["protocolParams"]["minFeeB"]
        fee = min(min_fee_b * 6, 2_000_000)

        # 4 Naive UTxO selections (smallest-first)
        selected: list[structs.UTXOData] = []
        running_total = 0

        for u in sorted(ada_utxos, key=lambda x: x.amount):
            selected.append(u)
            running_total += u.amount
            if running_total >= amount_required + fee:
                break

        if running_total < amount_required + fee:
            needed = amount_required + fee
            message = (
                f"Insufficient ADA for transaction. Required {needed}, available {running_total}."
            )
            raise exceptions.CLIError(message)

        # 5 compute change and final outputs
        change = running_total - (amount_required + fee)
        final_txouts = list(txouts)

        if change > 0:
            final_txouts.append(structs.TxOut(address=src_address, amount=change))

        # 6 Build CLI args for signed-transaction
        cli_args: list[str] = []

        for u in selected:
            cli_args.extend(["--tx-in", f"{u.utxo_hash}#{u.utxo_ix}"])

        for t in final_txouts:
            cli_args.extend(["--tx-out", f"{t.address}+{t.amount}"])

        cli_args.extend(["--fee", str(fee)])
        cli_args.extend(helpers._prepend_flag("--signing-key-file", signing_key_files))

        # 7 Delegate to bare wrapper for actual CLI call and file handling
        return self.gen_signed_tx(
            name=name,
            cli_args=cli_args,
            destination_dir=destination_dir,
        )

    def __repr__(self) -> str:
        return f"<TransactionGroup base={self._base}>"
