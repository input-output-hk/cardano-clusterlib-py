"""Group of subgroups for governance in Conway+ eras."""

import logging

from cardano_clusterlib import gov_action_group
from cardano_clusterlib import gov_committee_group
from cardano_clusterlib import gov_drep_group
from cardano_clusterlib import gov_vote_group
from cardano_clusterlib import types as itp

LOGGER = logging.getLogger(__name__)


class GovernanceGroup:
    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj

        # Groups of commands
        self._action_group: gov_action_group.GovActionGroup | None = None
        self._committee_group: gov_committee_group.GovCommitteeGroup | None = None
        self._drep_group: gov_drep_group.GovDrepGroup | None = None
        self._vote_group: gov_vote_group.GovVoteGroup | None = None

    @property
    def action(self) -> gov_action_group.GovActionGroup:
        """Action group."""
        if not self._action_group:
            self._action_group = gov_action_group.GovActionGroup(
                clusterlib_obj=self._clusterlib_obj
            )
        return self._action_group

    @property
    def committee(self) -> gov_committee_group.GovCommitteeGroup:
        """Committee group."""
        if not self._committee_group:
            self._committee_group = gov_committee_group.GovCommitteeGroup(
                clusterlib_obj=self._clusterlib_obj
            )
        return self._committee_group

    @property
    def drep(self) -> gov_drep_group.GovDrepGroup:
        """Drep group."""
        if not self._drep_group:
            self._drep_group = gov_drep_group.GovDrepGroup(clusterlib_obj=self._clusterlib_obj)
        return self._drep_group

    @property
    def vote(self) -> gov_vote_group.GovVoteGroup:
        """Vote group."""
        if not self._vote_group:
            self._vote_group = gov_vote_group.GovVoteGroup(clusterlib_obj=self._clusterlib_obj)
        return self._vote_group

    def get_anchor_data_hash(
        self,
        text: str = "",
        file_binary: itp.FileType | None = None,
        file_text: itp.FileType | None = None,
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
        script_file: itp.FileType | None = None,
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
