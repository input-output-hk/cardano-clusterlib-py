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

    def registration_certificate(self, cli_args: itp.UnpackableSequence) -> None:
        """Wrap the `stake-pool registration-certificate` command."""
        full_args = [*self._base, "registration-certificate", *cli_args]

        self._clusterlib_obj.cli(full_args, add_default_args=False)


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
