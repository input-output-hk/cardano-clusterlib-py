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

    def _get_cred_args(
        self,
        drep_script_hash: str = "",
        drep_vkey: str = "",
        drep_vkey_file: tp.Optional[itp.FileType] = None,
        drep_key_hash: str = "",
    ) -> tp.List[str]:
        """Get arguments for script or verification key."""
        if drep_script_hash:
            cred_args = ["--drep-script-hash", str(drep_script_hash)]
        elif drep_vkey:
            cred_args = ["--drep-verification-key", str(drep_vkey)]
        elif drep_vkey_file:
            cred_args = ["--drep-verification-key-file", str(drep_vkey_file)]
        elif drep_key_hash:
            cred_args = ["--drep-key-hash", str(drep_key_hash)]
        else:
            cred_args = []

        return cred_args

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
        drep_script_hash: str = "",
        drep_vkey: str = "",
        drep_vkey_file: tp.Optional[itp.FileType] = None,
        drep_key_hash: str = "",
    ) -> tp.List[tp.List[tp.Dict[str, tp.Any]]]:
        """Get the DRep state.

        When no key is provided, query all DReps.

        Args:
            drep_script_hash: DRep script hash (hex-encoded, optional).
            drep_vkey: DRep verification key (Bech32 or hex-encoded).
            drep_vkey_file: Filepath of the DRep verification key.
            drep_key_hash: DRep verification key hash (either Bech32-encoded or hex-encoded).

        Returns:
            List[List[Dict[str, Any]]]: DRep state.
        """
        cred_args = self._get_cred_args(
            drep_script_hash=drep_script_hash,
            drep_vkey=drep_vkey,
            drep_vkey_file=drep_vkey_file,
            drep_key_hash=drep_key_hash,
        )
        if not cred_args:
            cred_args = ["--all-dreps"]

        out: tp.List[tp.List[tp.Dict[str, tp.Any]]] = json.loads(
            self.query_cli(["drep-state", *cred_args])
        )
        return out

    def drep_stake_distribution(
        self,
        drep_script_hash: str = "",
        drep_vkey: str = "",
        drep_vkey_file: tp.Optional[itp.FileType] = None,
        drep_key_hash: str = "",
    ) -> tp.List[list]:
        """Get the DRep stake distribution.

        When no key is provided, query all DReps.

        Args:
            drep_script_hash: DRep script hash (hex-encoded, optional).
            drep_vkey: DRep verification key (Bech32 or hex-encoded).
            drep_vkey_file: Filepath of the DRep verification key.
            drep_key_hash: DRep verification key hash (either Bech32-encoded or hex-encoded).

        Returns:
            List[List[Dict[str, Any]]]: DRep stake distribution.
        """
        cred_args = self._get_cred_args(
            drep_script_hash=drep_script_hash,
            drep_vkey=drep_vkey,
            drep_vkey_file=drep_vkey_file,
            drep_key_hash=drep_key_hash,
        )
        if not cred_args:
            cred_args = ["--all-dreps"]

        out: tp.List[tp.List[tp.Dict[str, tp.Any]]] = json.loads(
            self.query_cli(["drep-stake-distribution", *cred_args])
        )
        return out

    def committee_state(self) -> tp.Dict[str, tp.Any]:
        """Get the committee state."""
        out: tp.Dict[str, tp.Any] = json.loads(self.query_cli(["committee-state"]))
        return out

    def treasury(self) -> int:
        """Get the treasury value."""
        return int(self.query_cli(["treasury"]))

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: clusterlib_obj={id(self._clusterlib_obj)}>"
