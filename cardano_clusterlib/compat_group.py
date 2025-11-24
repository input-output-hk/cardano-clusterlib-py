"""Group of subgroups for cardano-cli 'compatible' commands (legacy eras)."""

import logging

from cardano_clusterlib import compat_alonzo_group
from cardano_clusterlib import types as itp

LOGGER = logging.getLogger(__name__)


class CompatibleGroup:
    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj

        # Groups of commands per era
        self._alonzo_group: compat_alonzo_group.CompatibleAlonzoGroup | None = None
        # self._mary_group: compatible_mary_group.CompatibleMaryGroup | None = None
        # self._shelley_group: compatible_shelley_group.CompatibleShelleyGroup | None = None
        # ...

    @property
    def alonzo(self) -> compat_alonzo_group.CompatibleAlonzoGroup:
        if not self._alonzo_group:
            self._alonzo_group = compat_alonzo_group.CompatibleAlonzoGroup(
                clusterlib_obj=self._clusterlib_obj
            )
        return self._alonzo_group

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: clusterlib_obj={id(self._clusterlib_obj)}>"
