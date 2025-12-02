"""Shelley era compatible commands for `cardano-cli compatible shelley`."""

import logging
from typing import TYPE_CHECKING

from cardano_clusterlib import types as itp

if TYPE_CHECKING:
    from cardano_clusterlib.clusterlib_klass import ClusterLib

LOGGER = logging.getLogger(__name__)


class CompatibleShelleyGroup:
    """Shelley era compatible group."""

    def __init__(self, clusterlib_obj: "ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base_args = ("compatible", "shelley")

        self.stake_address = StakeAddressGroup(clusterlib_obj, self._base_args)
        self.stake_pool = StakePoolGroup(clusterlib_obj, self._base_args)
        self.governance = GovernanceGroup(clusterlib_obj, self._base_args)
        self.transaction = TransactionGroup(clusterlib_obj, self._base_args)

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}: base_args={self._base_args} "
            f"clusterlib_obj={id(self._clusterlib_obj)}>"
        )


class StakeAddressGroup:
    """`cardano-cli compatible shelley stake-address` commands."""

    def __init__(self, clusterlib_obj: "ClusterLib", base_args: tuple[str, str]) -> None:
        self._clusterlib_obj = clusterlib_obj
        # cardano-cli compatible shelley stake-address
        self._cli_args = ("cardano-cli", *base_args, "stake-address")

    def registration_certificate(
        self,
        cli_args: itp.UnpackableSequence,
    ) -> None:
        """Wrap the `stake-address registration-certificate` command."""
        full_args = [
            *self._cli_args,
            "registration-certificate",
            *cli_args,
        ]

        LOGGER.debug(
            "Running compatible shelley stake-address registration-certificate: %s",
            " ".join(str(a) for a in full_args),
        )

        self._clusterlib_obj.cli(full_args, add_default_args=False)

    def stake_delegation_certificate(
        self,
        cli_args: itp.UnpackableSequence,
    ) -> None:
        """Wrap the `stake-address stake-delegation-certificate` command."""
        full_args = [
            *self._cli_args,
            "stake-delegation-certificate",
            *cli_args,
        ]

        LOGGER.debug(
            "Running compatible shelley stake-address stake-delegation-certificate: %s",
            " ".join(str(a) for a in full_args),
        )

        self._clusterlib_obj.cli(full_args, add_default_args=False)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} cli_args={self._cli_args}>"


class StakePoolGroup:
    """`cardano-cli compatible shelley stake-pool` commands."""

    def __init__(self, clusterlib_obj: "ClusterLib", base_args: tuple[str, str]) -> None:
        self._clusterlib_obj = clusterlib_obj
        # cardano-cli compatible shelley stake-pool
        self._cli_args = ("cardano-cli", *base_args, "stake-pool")

    def registration_certificate(
        self,
        cli_args: itp.UnpackableSequence,
    ) -> None:
        """Wrap the `stake-pool registration-certificate` command."""
        full_args = [
            *self._cli_args,
            "registration-certificate",
            *cli_args,
        ]

        LOGGER.debug(
            "Running compatible shelley stake-pool registration-certificate: %s",
            " ".join(str(a) for a in full_args),
        )

        self._clusterlib_obj.cli(full_args, add_default_args=False)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} cli_args={self._cli_args}>"


class GovernanceGroup:
    """`cardano-cli compatible shelley governance` commands."""

    def __init__(self, clusterlib_obj: "ClusterLib", base_args: tuple[str, str]) -> None:
        self._clusterlib_obj = clusterlib_obj
        # cardano-cli compatible shelley governance
        self._cli_args = ("cardano-cli", *base_args, "governance")

    def create_mir_certificate(
        self,
        cli_args: itp.UnpackableSequence,
    ) -> None:
        """Wrap the `governance create-mir-certificate` command."""
        full_args = [
            *self._cli_args,
            "create-mir-certificate",
            *cli_args,
        ]

        LOGGER.debug(
            "Running compatible shelley governance create-mir-certificate: %s",
            " ".join(str(a) for a in full_args),
        )

        self._clusterlib_obj.cli(full_args, add_default_args=False)

    def create_genesis_key_delegation_certificate(
        self,
        cli_args: itp.UnpackableSequence,
    ) -> None:
        """Wrap the `governance create-genesis-key-delegation-certificate` command."""
        full_args = [
            *self._cli_args,
            "create-genesis-key-delegation-certificate",
            *cli_args,
        ]

        LOGGER.debug(
            "Running compatible shelley governance create-genesis-key-delegation-certificate: %s",
            " ".join(str(a) for a in full_args),
        )

        self._clusterlib_obj.cli(full_args, add_default_args=False)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} cli_args={self._cli_args}>"


class TransactionGroup:
    """Transaction commands for `cardano-cli compatible shelley transaction`."""

    def __init__(self, clusterlib_obj: "ClusterLib", base_args: tuple[str, str]) -> None:
        self._clusterlib_obj = clusterlib_obj
        # cardano-cli compatible shelley transaction
        self._cli_args = ("cardano-cli", *base_args, "transaction")

    def signed_transaction(
        self,
        cli_args: itp.UnpackableSequence,
    ) -> None:
        """Wrap the `transaction signed-transaction` command."""
        full_args = [
            *self._cli_args,
            "signed-transaction",
            *cli_args,
        ]

        LOGGER.debug(
            "Running compatible shelley transaction signed-transaction: %s",
            " ".join(str(a) for a in full_args),
        )

        self._clusterlib_obj.cli(full_args, add_default_args=False)

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} cli_args={self._cli_args} "
            f"clusterlib_obj={id(self._clusterlib_obj)}>"
        )
