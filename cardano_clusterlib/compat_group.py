"""Group of subgroups for cardano-cli 'compatible' commands (legacy eras)."""

import logging

from cardano_clusterlib import compat_common
from cardano_clusterlib import types as itp

LOGGER = logging.getLogger(__name__)


class CompatibleAlonzoGroup:
    """Wrapper exposing the generic compat groups for the Alonzo era."""

    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self.stake_address = compat_common.StakeAddressGroup(clusterlib_obj, "alonzo")
        self.stake_pool = compat_common.StakePoolGroup(clusterlib_obj, "alonzo")
        self.governance = compat_common.GovernanceGroup(clusterlib_obj, "alonzo")
        self.transaction = compat_common.TransactionGroup(clusterlib_obj, "alonzo")


class CompatibleBabbageGroup:
    """Wrapper exposing the generic compat groups for the Babbage era."""

    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self.stake_address = compat_common.StakeAddressGroup(clusterlib_obj, "babbage")
        self.stake_pool = compat_common.StakePoolGroup(clusterlib_obj, "babbage")
        self.governance = compat_common.GovernanceGroup(clusterlib_obj, "babbage")
        self.transaction = compat_common.TransactionGroup(clusterlib_obj, "babbage")


class CompatibleMaryGroup:
    """Wrapper exposing the generic compat groups for the Mary era."""

    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self.stake_address = compat_common.StakeAddressGroup(clusterlib_obj, "mary")
        self.stake_pool = compat_common.StakePoolGroup(clusterlib_obj, "mary")
        self.governance = compat_common.GovernanceGroup(clusterlib_obj, "mary")
        self.transaction = compat_common.TransactionGroup(clusterlib_obj, "mary")


class CompatibleShelleyGroup:
    """Wrapper exposing the generic compat groups for the Shelley era."""

    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self.stake_address = compat_common.StakeAddressGroup(clusterlib_obj, "shelley")
        self.stake_pool = compat_common.StakePoolGroup(clusterlib_obj, "shelley")
        self.governance = compat_common.GovernanceGroup(clusterlib_obj, "shelley")
        self.transaction = compat_common.TransactionGroup(clusterlib_obj, "shelley")


class CompatibleAllegraGroup:
    """Wrapper exposing the generic compat groups for the Allegra era."""

    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self.stake_address = compat_common.StakeAddressGroup(clusterlib_obj, "allegra")
        self.stake_pool = compat_common.StakePoolGroup(clusterlib_obj, "allegra")
        self.governance = compat_common.GovernanceGroup(clusterlib_obj, "allegra")
        self.transaction = compat_common.TransactionGroup(clusterlib_obj, "allegra")


class CompatibleGroup:
    """Top-level accessor for all compatible-era command groups."""

    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj

        self._shelley: CompatibleShelleyGroup | None = None
        self._allegra: CompatibleAllegraGroup | None = None
        self._mary: CompatibleMaryGroup | None = None
        self._alonzo: CompatibleAlonzoGroup | None = None
        self._babbage: CompatibleBabbageGroup | None = None

    @property
    def shelley(self) -> CompatibleShelleyGroup:
        if not self._shelley:
            self._shelley = CompatibleShelleyGroup(self._clusterlib_obj)
        return self._shelley

    @property
    def allegra(self) -> CompatibleAllegraGroup:
        if not self._allegra:
            self._allegra = CompatibleAllegraGroup(self._clusterlib_obj)
        return self._allegra

    @property
    def mary(self) -> CompatibleMaryGroup:
        if not self._mary:
            self._mary = CompatibleMaryGroup(self._clusterlib_obj)
        return self._mary

    @property
    def alonzo(self) -> CompatibleAlonzoGroup:
        if not self._alonzo:
            self._alonzo = CompatibleAlonzoGroup(self._clusterlib_obj)
        return self._alonzo

    @property
    def babbage(self) -> CompatibleBabbageGroup:
        if not self._babbage:
            self._babbage = CompatibleBabbageGroup(self._clusterlib_obj)
        return self._babbage
