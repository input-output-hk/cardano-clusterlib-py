"""Group of subgroups for governance in Conway+ eras."""

import logging
import typing as tp

from cardano_clusterlib import conway_gov_action_group
from cardano_clusterlib import conway_gov_committee_group
from cardano_clusterlib import conway_gov_drep_group
from cardano_clusterlib import conway_gov_query_group
from cardano_clusterlib import conway_gov_vote_group
from cardano_clusterlib import types as itp

LOGGER = logging.getLogger(__name__)


class ConwayGovGroup:
    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj

        # Groups of commands
        self._action_group: tp.Optional[conway_gov_action_group.ConwayGovActionGroup] = None
        self._committee_group: tp.Optional[conway_gov_committee_group.ConwayGovCommitteeGroup] = (
            None
        )
        self._drep_group: tp.Optional[conway_gov_drep_group.ConwayGovDrepGroup] = None
        self._query_group: tp.Optional[conway_gov_query_group.ConwayGovQueryGroup] = None
        self._vote_group: tp.Optional[conway_gov_vote_group.ConwayGovVoteGroup] = None

    @property
    def action(self) -> conway_gov_action_group.ConwayGovActionGroup:
        """Action group."""
        if not self._action_group:
            self._action_group = conway_gov_action_group.ConwayGovActionGroup(
                clusterlib_obj=self._clusterlib_obj
            )
        return self._action_group

    @property
    def committee(self) -> conway_gov_committee_group.ConwayGovCommitteeGroup:
        """Committee group."""
        if not self._committee_group:
            self._committee_group = conway_gov_committee_group.ConwayGovCommitteeGroup(
                clusterlib_obj=self._clusterlib_obj
            )
        return self._committee_group

    @property
    def drep(self) -> conway_gov_drep_group.ConwayGovDrepGroup:
        """Drep group."""
        if not self._drep_group:
            self._drep_group = conway_gov_drep_group.ConwayGovDrepGroup(
                clusterlib_obj=self._clusterlib_obj
            )
        return self._drep_group

    @property
    def query(self) -> conway_gov_query_group.ConwayGovQueryGroup:
        """Query group."""
        if not self._query_group:
            self._query_group = conway_gov_query_group.ConwayGovQueryGroup(
                clusterlib_obj=self._clusterlib_obj
            )
        return self._query_group

    @property
    def vote(self) -> conway_gov_vote_group.ConwayGovVoteGroup:
        """Vote group."""
        if not self._vote_group:
            self._vote_group = conway_gov_vote_group.ConwayGovVoteGroup(
                clusterlib_obj=self._clusterlib_obj
            )
        return self._vote_group

    def get_anchor_data_hash(
        self,
        text: str = "",
        file_binary: tp.Optional[itp.FileType] = None,
        file_text: tp.Optional[itp.FileType] = None,
    ) -> str:
        """Compute the hash of some anchor data.

        Args:
            text: A text to hash as UTF-8.
            file_binary: A path to the binary file to hash.
            file_text: A path to the text file to hash.

        Returns:
            str: A hash string.
        """
        if text:
            content_args = ["--text", text]
        elif file_binary:
            content_args = ["--file-binary", str(file_binary)]
        elif file_text:
            content_args = ["--file-text", str(file_text)]
        else:
            msg = "Either `text`, `file_binary` or `file_text` is needed."
            raise AssertionError(msg)

        out_hash = (
            self._clusterlib_obj.cli(
                ["cardano-cli", "hash", "anchor-data", *content_args], add_default_args=False
            )
            .stdout.rstrip()
            .decode("ascii")
        )

        return out_hash

    def get_script_hash(
        self,
        script_file: tp.Optional[itp.FileType] = None,
    ) -> str:
        """Compute the hash of a script.

        Args:
            script_file: A path to the text file to hash.

        Returns:
            str: A hash string.
        """
        # TODO: make it a top-level function to reflect `cardano-cli hash`
        out_hash = (
            self._clusterlib_obj.cli(
                ["cardano-cli", "hash", "script", "--script-file", str(script_file)],
                add_default_args=False,
            )
            .stdout.rstrip()
            .decode("ascii")
        )

        return out_hash

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: clusterlib_obj={id(self._clusterlib_obj)}>"
