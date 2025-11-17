"""Group of subgroups for 'compatible alonzo' commands."""

import logging

from cardano_clusterlib import types as itp
from cardano_clusterlib.compatilbe_group import compatible_alonzo_transaction_group

LOGGER = logging.getLogger(__name__)


class CompatibleAlonzoGroup:
    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj

        self._group_args = ("compatible", "alonzo")

        # Groups of commands within this era
        self._transaction_group: (
            compatible_alonzo_transaction_group.CompatibleAlonzoTransactionGroup | None
        ) = None
        # self._governance_group: CompatibleAlonzoGovernanceGroup | None = None
        # self._stake_address_group: CompatibleAlonzoStakeAddressGroup | None = None
        # self._stake_pool_group: CompatibleAlonzoStakePoolGroup | None = None

    @property
    def transaction(self) -> "compatible_alonzo_transaction_group.CompatibleAlonzoTransactionGroup":
        """Transaction group for Alonzo compatible commands."""
        if not self._transaction_group:
            self._transaction_group = (
                compatible_alonzo_transaction_group.CompatibleAlonzoTransactionGroup(
                    clusterlib_obj=self._clusterlib_obj,
                    group_args=self._group_args,
                )
            )
        return self._transaction_group

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}: group_args={self._group_args} "
            f"clusterlib_obj={id(self._clusterlib_obj)}>"
        )
