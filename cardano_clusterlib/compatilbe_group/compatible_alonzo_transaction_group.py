"""Transaction commands for 'cardano-cli compatible alonzo transaction'."""

import logging

from cardano_clusterlib import types as itp

LOGGER = logging.getLogger(__name__)


class CompatibleAlonzoTransactionGroup:
    def __init__(self, clusterlib_obj: "itp.ClusterLib", group_args: tuple[str, str]) -> None:
        """Group for 'compatible alonzo transaction' commands.

        Args:
            clusterlib_obj: Main ClusterLib instance.
            group_args: Fixed CLI prefix, e.g. ("compatible", "alonzo").
        """
        self._clusterlib_obj = clusterlib_obj
        # ("compatible", "alonzo")
        self._group_args = group_args

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
            f"<{self.__class__.__name__}: group_args={self._group_args} "
            f"clusterlib_obj={id(self._clusterlib_obj)}>"
        )
