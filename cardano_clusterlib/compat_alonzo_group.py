"""Alonzo era compatible commands for `cardano-cli compatible alonzo`."""

import logging
from typing import TYPE_CHECKING

from cardano_clusterlib import types as itp

if TYPE_CHECKING:
    from cardano_clusterlib.clusterlib_klass import ClusterLib

LOGGER = logging.getLogger(__name__)


class CompatibleAlonzoGroup:
    """
    A Single container for ALL Alonzo compatible commands.

    """

    def __init__(self, clusterlib_obj: "ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj
        self._base_args = ("compatible", "alonzo")

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
    """`cardano-cli compatible alonzo stake-address` commands."""

    def __init__(self, clusterlib_obj: "ClusterLib", base_args: tuple[str, str]) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._group_args = (*base_args, "stake-address")

    def registration_certificate(
            self,
            cli_args: itp.UnpackableSequence,
    ) -> None:
        """Wrapper for:
            cardano-cli compatible alonzo stake-address registration-certificate
        """
        full_args = [
            *self._group_args,
            "registration-certificate",
            *cli_args,
        ]

        LOGGER.debug(
            "Running compatible alonzo stake-address registration-certificate: %s",
            " ".join(str(a) for a in full_args),
        )

        self._clusterlib_obj.cli(full_args)

    def __repr__(self) -> str:
        return f"<StakeAddressGroup base={self._group_args}>"


class StakePoolGroup:
    """`cardano-cli compatible alonzo stake-pool` commands."""

    def __init__(self, clusterlib_obj: "ClusterLib", base_args: tuple[str, str]) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._group_args = (*base_args, "stake-pool")

    def run_raw(self, cli_args: itp.UnpackableSequence) -> None:
        """Generic low-level wrapper."""
        full_args = [*self._group_args, *cli_args]

        LOGGER.debug("Running compatible alonzo stake-pool: %s", " ".join(full_args))
        self._clusterlib_obj.cli(full_args)

    def __repr__(self) -> str:
        return f"<StakePoolGroup base={self._group_args}>"


class GovernanceGroup:
    """`cardano-cli compatible alonzo governance` commands."""

    def __init__(self, clusterlib_obj: "ClusterLib", base_args: tuple[str, str]) -> None:
        self._clusterlib_obj = clusterlib_obj
        self._group_args = (*base_args, "governance")

    def run_raw(self, cli_args: itp.UnpackableSequence) -> None:
        """Low-level wrapper."""
        full_args = [*self._group_args, *cli_args]

        LOGGER.debug("Running compatible alonzo governance: %s", " ".join(full_args))
        self._clusterlib_obj.cli(full_args)

    def __repr__(self) -> str:
        return f"<GovernanceGroup base={self._group_args}>"


class TransactionGroup:
    """Transaction commands for `cardano-cli compatible alonzo transaction`."""

    def __init__(self, clusterlib_obj: "ClusterLib", base_args: tuple[str, str]) -> None:
        """Group for 'compatible alonzo transaction' commands.

        Args:
            clusterlib_obj: Main ClusterLib instance.
            base_args: Fixed CLI prefix
        """
        self._clusterlib_obj = clusterlib_obj
        self._group_args = (*base_args, "transaction")

        #We have only sign-transaction command for now

    def signed_transaction(
        self,
        cli_args: itp.UnpackableSequence,
    ) -> None:
        """Low-level wrapper for `cardano-cli compatible alonzo transaction signed-transaction`."""
        full_args: list[str] = [
            *self._group_args,
            "transaction",
            "signed-transaction",
            *cli_args,
        ]

        LOGGER.debug(
            "Running compatible Alonzo signed-transaction: %s",
            " ".join(str(a) for a in full_args),
        )

        self._clusterlib_obj.cli(full_args)

    def __repr__(self) -> str:
        return (
            f"<CompatibleAlonzoTransactionGroup group_args={self._group_args} "
            f"clusterlib_obj={id(self._clusterlib_obj)}>"
        )
