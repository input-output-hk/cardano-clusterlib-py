"""Generic reusable classes for cardano-cli `compatible` commands."""

from typing import TYPE_CHECKING

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

    def _resolve_pool_vkey_args(
        self,
        *,
        stake_pool_vkey: str = "",
        stake_pool_extended_vkey: str = "",
        cold_vkey_file: itp.FileType | None = None,
    ) -> list[str]:
        """Resolve pool key identification."""
        if stake_pool_vkey:
            return ["--stake-pool-verification-key", stake_pool_vkey]
        if stake_pool_extended_vkey:
            return ["--stake-pool-verification-extended-key", stake_pool_extended_vkey]
        if cold_vkey_file:
            return ["--cold-verification-key-file", str(cold_vkey_file)]

        msg = (
            "One of stake_pool_vkey, stake_pool_extended_vkey, or cold_vkey_file must be provided."
        )
        raise ValueError(msg)

    def _resolve_vrf_args(
        self,
        *,
        vrf_vkey: str = "",
        vrf_vkey_file: itp.FileType | None = None,
    ) -> list[str]:
        """Resolve VRF key identification."""
        if vrf_vkey:
            return ["--vrf-verification-key", vrf_vkey]
        if vrf_vkey_file:
            return ["--vrf-verification-key-file", str(vrf_vkey_file)]

        msg = "One of vrf_vkey or vrf_vkey_file must be provided."
        raise ValueError(msg)

    def _resolve_reward_account_args(
        self,
        *,
        reward_vkey: str = "",
        reward_vkey_file: itp.FileType | None = None,
    ) -> list[str]:
        """Resolve reward account specification."""
        if reward_vkey:
            return ["--pool-reward-account-verification-key", reward_vkey]
        if reward_vkey_file:
            return ["--pool-reward-account-verification-key-file", str(reward_vkey_file)]

        msg = "One of reward_vkey or reward_vkey_file must be provided."
        raise ValueError(msg)

    def _resolve_owner_args(
        self,
        *,
        owner_vkey: str = "",
        owner_vkey_file: itp.FileType | None = None,
    ) -> list[str]:
        """Resolve owner stake key."""
        if owner_vkey:
            return ["--pool-owner-verification-key", owner_vkey]
        if owner_vkey_file:
            return ["--pool-owner-stake-verification-key-file", str(owner_vkey_file)]

        msg = "One of owner_vkey or owner_vkey_file must be provided."
        raise ValueError(msg)

    def registration_certificate(
        self,
        *,
        # pool identification
        stake_pool_vkey: str = "",
        stake_pool_extended_vkey: str = "",
        cold_vkey_file: itp.FileType | None = None,
        # VRF identification
        vrf_vkey: str = "",
        vrf_vkey_file: itp.FileType | None = None,
        # financials
        pool_pledge: int,
        pool_cost: int,
        pool_margin: str,
        # reward account
        reward_vkey: str = "",
        reward_vkey_file: itp.FileType | None = None,
        # owner
        owner_vkey: str = "",
        owner_vkey_file: itp.FileType | None = None,
        # relays
        relay_ipv4: str = "",
        relay_ipv6: str = "",
        relay_port: int | None = None,
        single_host_relay: str = "",
        multi_host_relay: str = "",
        # metadata
        metadata_url: str = "",
        metadata_hash: str = "",
        check_metadata_hash: bool = False,
        # output
        out_file: itp.FileType,
    ) -> None:
        """Wrap the compat stake-pool registration-certificate command."""
        # Required argument groups
        pool_args = self._resolve_pool_vkey_args(
            stake_pool_vkey=stake_pool_vkey,
            stake_pool_extended_vkey=stake_pool_extended_vkey,
            cold_vkey_file=cold_vkey_file,
        )

        vrf_args = self._resolve_vrf_args(
            vrf_vkey=vrf_vkey,
            vrf_vkey_file=vrf_vkey_file,
        )

        reward_args = self._resolve_reward_account_args(
            reward_vkey=reward_vkey,
            reward_vkey_file=reward_vkey_file,
        )

        owner_args = self._resolve_owner_args(
            owner_vkey=owner_vkey,
            owner_vkey_file=owner_vkey_file,
        )

        # Relay handling
        relay_args: list[str] = []

        if relay_ipv4:
            relay_args.extend(["--pool-relay-ipv4", relay_ipv4])
        if relay_ipv6:
            relay_args.extend(["--pool-relay-ipv6", relay_ipv6])
        if relay_port:
            relay_args.extend(["--pool-relay-port", str(relay_port)])

        if single_host_relay:
            relay_args.extend(["--single-host-pool-relay", single_host_relay])
            if relay_port:
                relay_args.extend(["--pool-relay-port", str(relay_port)])

        if multi_host_relay:
            relay_args.extend(["--multi-host-pool-relay", multi_host_relay])

        # Metadata arguments
        metadata_args: list[str] = []
        if metadata_url and metadata_hash:
            metadata_args.extend(
                [
                    "--metadata-url",
                    metadata_url,
                    "--metadata-hash",
                    metadata_hash,
                ]
            )
            if check_metadata_hash:
                metadata_args.append("--check-metadata-hash")

        # Build final CLI cmd
        cmd = [
            *self._base,
            "registration-certificate",
            *pool_args,
            *vrf_args,
            "--pool-pledge",
            str(pool_pledge),
            "--pool-cost",
            str(pool_cost),
            "--pool-margin",
            str(pool_margin),
            *reward_args,
            *owner_args,
            *relay_args,
            *metadata_args,
            "--out-file",
            str(out_file),
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)


class GovernanceGroup:
    """Generic governance group for all compatible eras."""

    def __init__(self, clusterlib_obj: "ClusterLib", era: str) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base = ("cardano-cli", "compatible", era, "governance")

    def _resolve_mir_direct_args(
        self,
        *,
        reserves: bool,
        treasury: bool,
        stake_address: str | None,
        reward: int | None,
        out_file: itp.FileType,
    ) -> list[str] | None:
        """Resolve direct MIR mode args (no subcommand).

        Direct mode syntax:
            (--reserves | --treasury)
            --stake-address ADDRESS
            --reward LOVELACE
            --out-file FILEPATH
        """
        # No direct mode selected
        if not reserves and not treasury:
            return None

        # Invalid: both pots selected
        if reserves and treasury:
            msg = "Cannot specify both `reserves` and `treasury` in direct MIR mode."
            raise ValueError(msg)

        if not stake_address:
            msg = "`stake_address` is required in direct MIR mode."
            raise ValueError(msg)

        if reward is None:
            msg = "`reward` is required in direct MIR mode."
            raise ValueError(msg)

        pot_flag = "--reserves" if reserves else "--treasury"

        args: list[str] = [
            pot_flag,
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
        """Arguments for `create-mir-certificate stake-addresses`."""
        if not stake_address:
            msg = "`stake_address` is required for 'stake-addresses' MIR subcommand."
            raise ValueError(msg)

        if reward is None:
            msg = "`reward` is required for 'stake-addresses' MIR subcommand."
            raise ValueError(msg)

        if funds not in ("reserves", "treasury"):
            msg = "`funds` must be either 'reserves' or 'treasury' for 'stake-addresses'."
            raise ValueError(msg)

        args: list[str] = [
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
        """Arguments for `create-mir-certificate transfer-to-treasury`."""
        if transfer_amt is None:
            msg = "`transfer_amt` is required for 'transfer-to-treasury' MIR subcommand."
            raise ValueError(msg)

        args: list[str] = [
            "transfer-to-treasury",
            "--transfer",
            str(transfer_amt),
            "--out-file",
            str(out_file),
        ]
        return args

    def _mir_transfer_to_rewards_args(
        self,
        *,
        transfer_amt: int | None,
        out_file: itp.FileType,
    ) -> list[str]:
        """Arguments for `create-mir-certificate transfer-to-rewards`."""
        if transfer_amt is None:
            msg = "`transfer_amt` is required for 'transfer-to-rewards' MIR subcommand."
            raise ValueError(msg)

        args: list[str] = [
            "transfer-to-rewards",
            "--transfer",
            str(transfer_amt),
            "--out-file",
            str(out_file),
        ]
        return args

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
        """Resolve MIR subcommand arguments, if any.

        Supported subcommands:
          * stake-addresses
          * transfer-to-treasury
          * transfer-to-rewards
        """
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
        # Direct MIR mode
        reserves: bool = False,
        treasury: bool = False,
        reward: int | None = None,
        stake_address: str | None = None,
        # Subcommand mode
        subcommand: str | None = None,
        transfer_amt: int | None = None,
        funds: str | None = None,
        # Output
        out_file: itp.FileType,
    ) -> None:
        """Wrap the `governance create-mir-certificate` command (compatible eras).

        Two usage modes:

        1. Direct MIR:
           * `reserves` or `treasury` (exactly one)
           * `stake_address`
           * `reward`
           * `out_file`

        2. Subcommands:
           * `subcommand="stake-addresses"`, `funds=("reserves"|"treasury")`,
             `stake_address`, `reward`, `out_file`
           * `subcommand="transfer-to-treasury"`, `transfer_amt`, `out_file`
           * `subcommand="transfer-to-rewards"`, `transfer_amt`, `out_file`
        """
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

        # Cannot mix modes
        if direct_args and subcmd_args:
            msg = "Cannot mix direct MIR mode with MIR subcommand mode."
            raise ValueError(msg)

        if not direct_args and not subcmd_args:
            msg = (
                "No MIR mode selected. Provide either direct MIR parameters "
                "(reserves/treasury + stake_address + reward) "
                "or a valid MIR subcommand."
            )
            raise ValueError(msg)

        final_args = direct_args or subcmd_args
        assert final_args is not None

        cmd = [
            *self._base,
            "create-mir-certificate",
            *final_args,
        ]

        self._clusterlib_obj.cli(cmd, add_default_args=False)

    def _resolve_genesis_key_args(
        self,
        *,
        genesis_vkey: str = "",
        genesis_vkey_file: itp.FileType | None = None,
        genesis_vkey_hash: str = "",
    ) -> list[str]:
        """Resolve genesis verification key specification."""
        if genesis_vkey:
            return ["--genesis-verification-key", genesis_vkey]

        if genesis_vkey_file:
            return ["--genesis-verification-key-file", str(genesis_vkey_file)]

        if genesis_vkey_hash:
            return ["--genesis-verification-key-hash", genesis_vkey_hash]

        msg = (
            "One of genesis_vkey, genesis_vkey_file or genesis_vkey_hash "
            "must be provided for genesis key delegation."
        )
        raise ValueError(msg)

    def _resolve_delegate_key_args(
        self,
        *,
        delegate_vkey: str = "",
        delegate_vkey_file: itp.FileType | None = None,
        delegate_vkey_hash: str = "",
    ) -> list[str]:
        """Resolve delegate verification key specification."""
        if delegate_vkey:
            return ["--genesis-delegate-verification-key", delegate_vkey]

        if delegate_vkey_file:
            return ["--genesis-delegate-verification-key-file", str(delegate_vkey_file)]

        if delegate_vkey_hash:
            return ["--genesis-delegate-verification-key-hash", delegate_vkey_hash]

        msg = (
            "One of delegate_vkey, delegate_vkey_file or delegate_vkey_hash "
            "must be provided for genesis key delegation."
        )
        raise ValueError(msg)

    def _resolve_vrf_key_args(
        self,
        *,
        vrf_vkey: str = "",
        vrf_vkey_file: itp.FileType | None = None,
        vrf_vkey_hash: str = "",
    ) -> list[str]:
        """Resolve VRF key specification."""
        if vrf_vkey:
            return ["--vrf-verification-key", vrf_vkey]

        if vrf_vkey_file:
            return ["--vrf-verification-key-file", str(vrf_vkey_file)]

        if vrf_vkey_hash:
            return ["--vrf-verification-key-hash", vrf_vkey_hash]

        msg = (
            "One of vrf_vkey, vrf_vkey_file or vrf_vkey_hash "
            "must be provided for genesis key delegation."
        )
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
        """Wrap the `governance create-genesis-key-delegation-certificate` command."""
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
