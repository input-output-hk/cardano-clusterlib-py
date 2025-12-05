"""Generic reusable classes for cardano-cli `compatible` commands."""

import pathlib as pl
from typing import TYPE_CHECKING

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
from cardano_clusterlib import types as itp

if TYPE_CHECKING:
    from cardano_clusterlib.clusterlib_klass import ClusterLib


class StakeAddressGroup:
    """Generic stake-address group for all compatible eras."""

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
        """Resolve stake key CLI args for registration & delegation."""
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
        msg = (
            "One of stake_vkey, stake_vkey_file, stake_key_hash, "
            "stake_script_file or stake_address must be provided."
        )
        raise ValueError(msg)

    def registration_certificate(
        self,
        *,
        stake_vkey: str = "",
        stake_vkey_file: itp.FileType | None = None,
        stake_key_hash: str = "",
        stake_script_file: itp.FileType | None = None,
        stake_address: str | None = None,
        out_file: itp.FileType,
    ) -> None:
        """Wrap the legacy stake-address registration-certificate command."""
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
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)

    def delegation_certificate(
        self,
        *,
        stake_vkey: str = "",
        stake_vkey_file: itp.FileType | None = None,
        stake_key_hash: str = "",
        stake_script_file: itp.FileType | None = None,
        stake_address: str | None = None,
        stake_pool_vkey: str = "",
        cold_vkey_file: itp.FileType | None = None,
        stake_pool_id: str = "",
        out_file: itp.FileType,
    ) -> None:
        """Wrap the legacy stake-address stake-delegation-certificate command."""
        stake_args = self._resolve_stake_key_args(
            stake_vkey=stake_vkey,
            stake_vkey_file=stake_vkey_file,
            stake_key_hash=stake_key_hash,
            stake_script_file=stake_script_file,
            stake_address=stake_address,
        )

        if stake_pool_vkey:
            pool_args = ["--stake-pool-verification-key", stake_pool_vkey]
        elif cold_vkey_file:
            pool_args = ["--cold-verification-key-file", str(cold_vkey_file)]
        elif stake_pool_id:
            pool_args = ["--stake-pool-id", stake_pool_id]
        else:
            msg = "One of stake_pool_vkey, cold_vkey_file or stake_pool_id must be provided."
            raise ValueError(msg)

        cmd = [
            *self._base,
            "stake-delegation-certificate",
            *stake_args,
            *pool_args,
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)


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

    def _resolve_pparam_args(
        self,
        *,
        epoch: int | None = None,
        genesis_vkey_file: itp.FileType | None = None,
        pparams: dict[str, object] | None = None,
    ) -> list[str]:
        """Resolve protocol parameter update CLI arguments."""
        if epoch is None:
            message = "The `epoch` parameter is required for protocol parameters update."
            raise ValueError(message)

        if not genesis_vkey_file:
            message = "`genesis_vkey_file` is required for protocol parameters update."
            raise ValueError(message)

        if not pparams:
            message = "At least one protocol parameter must be provided."
            raise ValueError(message)

        args: list[str] = ["--epoch", str(epoch)]

        for flag, value in pparams.items():
            if value is None:
                continue
            args.extend([flag, str(value)])

        args.extend(["--genesis-verification-key-file", str(genesis_vkey_file)])

        return args

    def create_protocol_parameters_update(
        self,
        *,
        epoch: int,
        genesis_vkey_file: itp.FileType,
        out_file: itp.FileType,
        **pparams: object,
    ) -> None:
        """Wrap the protocol parameters update command."""
        flag_map = {
            "min_fee_linear": "--min-fee-linear",
            "min_fee_constant": "--min-fee-constant",
            "max_block_body_size": "--max-block-body-size",
            "max_tx_size": "--max-tx-size",
            "max_block_header_size": "--max-block-header-size",
            "key_reg_deposit_amt": "--key-reg-deposit-amt",
            "pool_reg_deposit": "--pool-reg-deposit",
            "pool_retirement_epoch_interval": "--pool-retirement-epoch-interval",
            "number_of_pools": "--number-of-pools",
            "pool_influence": "--pool-influence",
            "treasury_expansion": "--treasury-expansion",
            "monetary_expansion": "--monetary-expansion",
            "min_pool_cost": "--min-pool-cost",
            "price_execution_steps": "--price-execution-steps",
            "price_execution_memory": "--price-execution-memory",
            "max_tx_execution_units": "--max-tx-execution-units",
            "max_block_execution_units": "--max-block-execution-units",
            "max_value_size": "--max-value-size",
            "collateral_percent": "--collateral-percent",
            "max_collateral_inputs": "--max-collateral-inputs",
            "protocol_major_version": "--protocol-major-version",
            "protocol_minor_version": "--protocol-minor-version",
            "utxo_cost_per_byte": "--utxo-cost-per-byte",
            "cost_model_file": "--cost-model-file",
        }

        pparam_args: dict[str, object] = {}

        for py_key, value in pparams.items():
            if py_key not in flag_map:
                msg = f"Unknown protocol parameter: {py_key}"
                raise ValueError(msg)
            if value is not None:
                pparam_args[flag_map[py_key]] = value

        resolved_args = self._resolve_pparam_args(
            epoch=epoch,
            genesis_vkey_file=genesis_vkey_file,
            pparams=pparam_args,
        )

        cmd = [
            *self._base,
            "create-protocol-parameters-update",
            *resolved_args,
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)


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
        out_file: itp.FileType,
    ) -> list[str] | None:
        if not reserves and not treasury:
            return None

        if reserves and treasury:
            msg = "Cannot specify both `reserves` and `treasury` in direct MIR mode."
            raise ValueError(msg)

        if not stake_address:
            msg = "`stake_address` is required in direct MIR mode."
            raise ValueError(msg)

        if reward is None:
            msg = "`reward` is required in direct MIR mode."
            raise ValueError(msg)

        flag = "--reserves" if reserves else "--treasury"

        args = [
            flag,
            "--stake-address",
            stake_address,
            "--reward",
            str(reward),
            "--out-file",
            str(out_file),
        ]
        return args

    def _mir_stake_addresses_args(
        self,
        *,
        stake_address: str | None,
        reward: int | None,
        funds: str | None,
        out_file: itp.FileType,
    ) -> list[str]:
        if not stake_address:
            msg = "`stake_address` is required for 'stake-addresses' MIR subcommand."
            raise ValueError(msg)

        if reward is None:
            msg = "`reward` is required for 'stake-addresses' MIR subcommand."
            raise ValueError(msg)

        if funds not in ("reserves", "treasury"):
            msg = "`funds` must be either 'reserves' or 'treasury' for 'stake-addresses'."
            raise ValueError(msg)

        args = [
            "stake-addresses",
            f"--{funds}",
            "--stake-address",
            stake_address,
            "--reward",
            str(reward),
            "--out-file",
            str(out_file),
        ]
        return args

    def _mir_transfer_to_treasury_args(
        self,
        *,
        transfer_amt: int | None,
        out_file: itp.FileType,
    ) -> list[str]:
        if transfer_amt is None:
            msg = "`transfer_amt` is required for 'transfer-to-treasury' MIR subcommand."
            raise ValueError(msg)

        return [
            "transfer-to-treasury",
            "--transfer",
            str(transfer_amt),
            "--out-file",
            str(out_file),
        ]

    def _mir_transfer_to_rewards_args(
        self,
        *,
        transfer_amt: int | None,
        out_file: itp.FileType,
    ) -> list[str]:
        if transfer_amt is None:
            msg = "`transfer_amt` is required for 'transfer-to-rewards' MIR subcommand."
            raise ValueError(msg)

        return [
            "transfer-to-rewards",
            "--transfer",
            str(transfer_amt),
            "--out-file",
            str(out_file),
        ]

    def _resolve_mir_subcommand_args(
        self,
        *,
        subcommand: str | None,
        stake_address: str | None,
        reward: int | None,
        transfer_amt: int | None,
        funds: str | None,
        out_file: itp.FileType,
    ) -> list[str] | None:
        if not subcommand:
            return None

        if subcommand == "stake-addresses":
            return self._mir_stake_addresses_args(
                stake_address=stake_address,
                reward=reward,
                funds=funds,
                out_file=out_file,
            )

        if subcommand == "transfer-to-treasury":
            return self._mir_transfer_to_treasury_args(
                transfer_amt=transfer_amt,
                out_file=out_file,
            )

        if subcommand == "transfer-to-rewards":
            return self._mir_transfer_to_rewards_args(
                transfer_amt=transfer_amt,
                out_file=out_file,
            )

        msg = f"Unknown MIR subcommand: {subcommand}"
        raise ValueError(msg)

    def create_mir_certificate(
        self,
        *,
        reserves: bool = False,
        treasury: bool = False,
        reward: int | None = None,
        stake_address: str | None = None,
        subcommand: str | None = None,
        transfer_amt: int | None = None,
        funds: str | None = None,
        out_file: itp.FileType,
    ) -> None:
        direct_args = self._resolve_mir_direct_args(
            reserves=reserves,
            treasury=treasury,
            stake_address=stake_address,
            reward=reward,
            out_file=out_file,
        )

        subcmd_args = self._resolve_mir_subcommand_args(
            subcommand=subcommand,
            stake_address=stake_address,
            reward=reward,
            transfer_amt=transfer_amt,
            funds=funds,
            out_file=out_file,
        )

        if direct_args and subcmd_args:
            msg = "Cannot mix direct MIR mode with MIR subcommand mode."
            raise ValueError(msg)

        if not direct_args and not subcmd_args:
            msg = (
                "No MIR mode selected. Provide either direct MIR parameters "
                "or a valid MIR subcommand."
            )
            raise ValueError(msg)

        if direct_args is not None:
            final_args: list[str] = direct_args
        else:
            msg = "Internal error: MIR subcommand arguments missing."
            if subcmd_args is None:
                raise ValueError(msg)
            final_args = subcmd_args

        cmd = [
            *self._base,
            "create-mir-certificate",
            *final_args,
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)

        self._clusterlib_obj.cli(cmd, add_default_args=False)

        self._clusterlib_obj.cli(cmd, add_default_args=False)

    def _resolve_genesis_key_args(
        self,
        *,
        genesis_vkey: str = "",
        genesis_vkey_file: itp.FileType | None = None,
        genesis_vkey_hash: str = "",
    ) -> list[str]:
        if genesis_vkey:
            return ["--genesis-verification-key", genesis_vkey]

        if genesis_vkey_file:
            return ["--genesis-verification-key-file", str(genesis_vkey_file)]

        if genesis_vkey_hash:
            return ["--genesis-verification-key-hash", genesis_vkey_hash]

        msg = "One of genesis_vkey, genesis_vkey_file or genesis_vkey_hash must be provided."
        raise ValueError(msg)

    def _resolve_delegate_key_args(
        self,
        *,
        delegate_vkey: str = "",
        delegate_vkey_file: itp.FileType | None = None,
        delegate_vkey_hash: str = "",
    ) -> list[str]:
        if delegate_vkey:
            return ["--genesis-delegate-verification-key", delegate_vkey]

        if delegate_vkey_file:
            return ["--genesis-delegate-verification-key-file", str(delegate_vkey_file)]

        if delegate_vkey_hash:
            return ["--genesis-delegate-verification-key-hash", delegate_vkey_hash]

        msg = "One of delegate_vkey, delegate_vkey_file or delegate_vkey_hash must be provided."
        raise ValueError(msg)

    def _resolve_vrf_key_args(
        self,
        *,
        vrf_vkey: str = "",
        vrf_vkey_file: itp.FileType | None = None,
        vrf_vkey_hash: str = "",
    ) -> list[str]:
        if vrf_vkey:
            return ["--vrf-verification-key", vrf_vkey]

        if vrf_vkey_file:
            return ["--vrf-verification-key-file", str(vrf_vkey_file)]

        if vrf_vkey_hash:
            return ["--vrf-verification-key-hash", vrf_vkey_hash]

        msg = "One VRF key argument must be provided."
        raise ValueError(msg)

    def create_genesis_key_delegation_certificate(
        self,
        *,
        genesis_vkey: str = "",
        genesis_vkey_file: itp.FileType | None = None,
        genesis_vkey_hash: str = "",
        delegate_vkey: str = "",
        delegate_vkey_file: itp.FileType | None = None,
        delegate_vkey_hash: str = "",
        vrf_vkey: str = "",
        vrf_vkey_file: itp.FileType | None = None,
        vrf_vkey_hash: str = "",
        out_file: itp.FileType,
    ) -> None:
        genesis_args = self._resolve_genesis_key_args(
            genesis_vkey=genesis_vkey,
            genesis_vkey_file=genesis_vkey_file,
            genesis_vkey_hash=genesis_vkey_hash,
        )

        delegate_args = self._resolve_delegate_key_args(
            delegate_vkey=delegate_vkey,
            delegate_vkey_file=delegate_vkey_file,
            delegate_vkey_hash=delegate_vkey_hash,
        )

        vrf_args = self._resolve_vrf_key_args(
            vrf_vkey=vrf_vkey,
            vrf_vkey_file=vrf_vkey_file,
            vrf_vkey_hash=vrf_vkey_hash,
        )

        cmd = [
            *self._base,
            "create-genesis-key-delegation-certificate",
            *genesis_args,
            *delegate_args,
            *vrf_args,
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)


class TransactionGroup:
    """Generic transaction group for all compatible eras."""

    def __init__(self, clusterlib_obj: "ClusterLib", era: str) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base = ("cardano-cli", "compatible", era, "transaction")

    def signed_transaction(self, cli_args: itp.UnpackableSequence) -> None:
        """Wrap the `transaction signed-transaction` command."""
        full_args = [*self._base, "signed-transaction", *cli_args]

        self._clusterlib_obj.cli(full_args, add_default_args=False)
