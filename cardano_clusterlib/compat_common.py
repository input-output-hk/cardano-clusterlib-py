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

    def create_mir_certificate(self, cli_args: itp.UnpackableSequence) -> None:
        """Wrap the `governance create-mir-certificate` command."""
        full_args = [*self._base, "create-mir-certificate", *cli_args]

        self._clusterlib_obj.cli(full_args, add_default_args=False)

    def create_genesis_key_delegation_certificate(self, cli_args: itp.UnpackableSequence) -> None:
        """Wrap the `governance create-genesis-key-delegation-certificate` command."""
        full_args = [*self._base, "create-genesis-key-delegation-certificate", *cli_args]

        self._clusterlib_obj.cli(full_args, add_default_args=False)


class TransactionGroup:
    """Generic transaction group for all compatible eras."""

    def __init__(self, clusterlib_obj: "ClusterLib", era: str) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base = ("cardano-cli", "compatible", era, "transaction")

    def signed_transaction(self, cli_args: itp.UnpackableSequence) -> None:
        """Wrap the `transaction signed-transaction` command."""
        full_args = [*self._base, "signed-transaction", *cli_args]

        self._clusterlib_obj.cli(full_args, add_default_args=False)
