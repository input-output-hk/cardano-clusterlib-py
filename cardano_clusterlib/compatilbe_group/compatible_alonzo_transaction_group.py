"""Transaction commands for 'cardano-cli compatible alonzo transaction'."""

import logging
from typing import Sequence

from cardano_clusterlib import types as itp

LOGGER = logging.getLogger(__name__)


class CompatibleAlonzoTransactionGroup:
    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj

    def build_raw(
        self,
        txins: Sequence[str],
        txouts: Sequence[str],
        out_file: itp.FileType,
        extra_args: Sequence[str] | None = None,
    ) -> None:
        """Simple wrapper for `cardano-cli compatible alonzo transaction build-raw`.
        """
        if not txins:
            msg = "`txins` must not be empty for compatible transaction build-raw."
            raise ValueError(msg)

        extra_args = extra_args or ()

        cmd: list[str] = [
            "cardano-cli",
            "compatible",
            "alonzo",
            "transaction",
            "build-raw",
        ]

        for txin in txins:
            cmd.extend(["--tx-in", txin])

        for txout in txouts:
            cmd.extend(["--tx-out", txout])

        cmd.extend(["--out-file", str(out_file)])
        cmd.extend(list(extra_args))

        LOGGER.debug("Running compatible Alonzo transaction build-raw: %s", " ".join(cmd))

        self._clusterlib_obj.cli(cmd)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: clusterlib_obj={id(self._clusterlib_obj)}>"
