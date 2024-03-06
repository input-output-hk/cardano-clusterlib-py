"""Group of methods for Conway governance query commands."""

import json
import logging
import typing as tp

from cardano_clusterlib import types as itp

LOGGER = logging.getLogger(__name__)


class ConwayGovQueryGroup:
    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj
        self._group_args = ("query",)

    def _get_key_args(
        self,
        drep_vkey: str = "",
        drep_vkey_file: tp.Optional[itp.FileType] = None,
        drep_key_hash: str = "",
    ) -> tp.List[str]:
        """Get arguments for verification key."""
        if drep_vkey:
            key_args = ["--drep-verification-key", str(drep_vkey)]
        elif drep_vkey_file:
            key_args = ["--drep-verification-key-file", str(drep_vkey_file)]
        elif drep_key_hash:
            key_args = ["--drep-key-hash", str(drep_key_hash)]
        else:
            key_args = []

        return key_args

    def query_cli(
        self, cli_args: itp.UnpackableSequence, cli_sub_args: itp.UnpackableSequence = ()
    ) -> str:
        """Run the `cardano-cli conway governance query` command."""
        stdout = self._clusterlib_obj.cli(
            [
                *self._group_args,
                *cli_args,
                *self._clusterlib_obj.magic_args,
                *self._clusterlib_obj.socket_args,
                *cli_sub_args,
            ]
        ).stdout
        stdout_dec = stdout.decode("utf-8") if stdout else ""
        return stdout_dec

    def constitution(self) -> tp.Dict[str, tp.Any]:
        """Get the constitution."""
        out: tp.Dict[str, tp.Any] = json.loads(self.query_cli(["constitution"]))
        return out

    def gov_state(self) -> tp.Dict[str, tp.Any]:
        """Get the governance state."""
        out: tp.Dict[str, tp.Any] = json.loads(self.query_cli(["gov-state"]))
        return out

    def drep_state(
        self,
        drep_vkey: str = "",
        drep_vkey_file: tp.Optional[itp.FileType] = None,
        drep_key_hash: str = "",
    ) -> tp.List[tp.List[tp.Dict[str, tp.Any]]]:
        """Get the DRep state.

        When no key is provided, query all DReps.

        Args:
            drep_vkey: DRep verification key (Bech32 or hex-encoded).
            drep_vkey_file: Filepath of the DRep verification key.
            drep_key_hash: DRep verification key hash (either Bech32-encoded or hex-encoded).

        Returns:
            List[List[Dict[str, Any]]]: DRep state.
        """
        key_args = self._get_key_args(
            drep_vkey=drep_vkey,
            drep_vkey_file=drep_vkey_file,
            drep_key_hash=drep_key_hash,
        )
        if not key_args:
            key_args = ["--all-dreps"]

        out: tp.List[tp.List[tp.Dict[str, tp.Any]]] = json.loads(
            self.query_cli(["drep-state", *key_args])
        )
        return out

    def drep_stake_distribution(
        self,
        drep_vkey: str = "",
        drep_vkey_file: tp.Optional[itp.FileType] = None,
        drep_key_hash: str = "",
    ) -> tp.List[list]:
        """Get the DRep stake distribution.

        When no key is provided, query all DReps.

        Args:
            drep_vkey: DRep verification key (Bech32 or hex-encoded).
            drep_vkey_file: Filepath of the DRep verification key.
            drep_key_hash: DRep verification key hash (either Bech32-encoded or hex-encoded).

        Returns:
            List[List[Dict[str, Any]]]: DRep stake distribution.
        """
        key_args = self._get_key_args(
            drep_vkey=drep_vkey,
            drep_vkey_file=drep_vkey_file,
            drep_key_hash=drep_key_hash,
        )
        if not key_args:
            key_args = ["--all-dreps"]

        out: tp.List[tp.List[tp.Dict[str, tp.Any]]] = json.loads(
            self.query_cli(["drep-stake-distribution", *key_args])
        )
        return out

    def committee_state(self) -> tp.Dict[str, tp.Any]:
        """Get the committee state."""
        out: tp.Dict[str, tp.Any] = json.loads(self.query_cli(["committee-state"]))
        return out

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: clusterlib_obj={id(self._clusterlib_obj)}>"
