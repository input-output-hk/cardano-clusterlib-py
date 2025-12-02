"""Group of subgroups for cardano-cli 'compatible' commands (legacy eras)."""

import logging

from cardano_clusterlib import compat_alonzo_group
from cardano_clusterlib import compat_babbage_group
from cardano_clusterlib import compat_mary_group
from cardano_clusterlib import compat_shelley_group
from cardano_clusterlib import types as itp

LOGGER = logging.getLogger(__name__)


class CompatibleGroup:
    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj

        # Groups of commands per era
        self._alonzo_group: compat_alonzo_group.CompatibleAlonzoGroup | None = None
        self._babbage_group: compat_babbage_group.CompatibleBabbageGroup | None = None
        self._mary_group: compat_mary_group.CompatibleMaryGroup | None = None
        self._shelley_group: compat_shelley_group.CompatibleShelleyGroup | None = None

    @property
    def alonzo(self) -> compat_alonzo_group.CompatibleAlonzoGroup:
        if not self._alonzo_group:
            self._alonzo_group = compat_alonzo_group.CompatibleAlonzoGroup(
                clusterlib_obj=self._clusterlib_obj
            )
        return self._alonzo_group

    @property
    def babbage(self) -> compat_babbage_group.CompatibleBabbageGroup:
        if not self._babbage_group:
            self._babbage_group = compat_babbage_group.CompatibleBabbageGroup(
                clusterlib_obj=self._clusterlib_obj
            )
        return self._babbage_group

    @property
    def mary(self) -> compat_mary_group.CompatibleMaryGroup:
        if not self._mary_group:
            self._mary_group = compat_mary_group.CompatibleMaryGroup(
                clusterlib_obj=self._clusterlib_obj
            )
        return self._mary_group

    @property
    def shelley(self) -> compat_shelley_group.CompatibleShelleyGroup:
        if not self._shelley_group:
            self._shelley_group = compat_shelley_group.CompatibleShelleyGroup(
                clusterlib_obj=self._clusterlib_obj
            )
        return self._shelley_group

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: clusterlib_obj={id(self._clusterlib_obj)}>"
