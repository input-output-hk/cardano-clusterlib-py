"""Group of methods for Conway governance vote commands."""
import json
import logging
import pathlib as pl
import typing as tp

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import helpers
from cardano_clusterlib import types as itp


LOGGER = logging.getLogger(__name__)


class ConwayGovVoteGroup:
    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj
        self._group_args = ("governance", "vote")

    def create(  # noqa: C901
        self,
        vote_name: str,
        action_txid: str,
        action_ix: int,
        vote_yes: bool = False,
        vote_no: bool = False,
        vote_abstain: bool = False,
        drep_vkey: str = "",
        drep_vkey_file: tp.Optional[itp.FileType] = None,
        drep_key_hash: str = "",
        stake_pool_vkey: str = "",
        cold_vkey_file: tp.Optional[itp.FileType] = None,
        stake_pool_id: str = "",
        cc_hot_vkey: str = "",
        cc_hot_vkey_file: tp.Optional[itp.FileType] = None,
        cc_hot_key_hash: str = "",
        anchor_url: str = "",
        anchor_data_hash: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Create a governance action vote."""
        # pylint: disable=too-many-arguments,too-many-branches
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{vote_name}.vote"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        if vote_yes:
            vote_args = ["--yes"]
        elif vote_no:
            vote_args = ["--no"]
        elif vote_abstain:
            vote_args = ["--abstain"]
        else:
            raise AssertionError("No vote was specified.")

        gov_action_args = [
            "--governance-action-tx-id",
            str(action_txid),
            "--governance-action-index",
            str(action_ix),
        ]

        if drep_vkey:
            key_args = ["--drep-verification-key", str(drep_vkey)]
        elif drep_vkey_file:
            key_args = ["--drep-verification-key-file", str(drep_vkey_file)]
        elif drep_key_hash:
            key_args = ["--drep-key-hash", str(drep_key_hash)]
        elif stake_pool_vkey:
            key_args = ["--stake-pool-verification-key", str(stake_pool_vkey)]
        elif cold_vkey_file:
            key_args = ["--cold-verification-key-file", str(cold_vkey_file)]
        elif stake_pool_id:
            key_args = ["--stake-pool-id", str(stake_pool_id)]
        elif cc_hot_vkey:
            key_args = ["--cc-hot-verification-key", str(cc_hot_vkey)]
        elif cc_hot_vkey_file:
            key_args = ["--cc-hot-verification-key-file", str(cc_hot_vkey_file)]
        elif cc_hot_key_hash:
            key_args = ["--cc-hot-key-hash", str(cc_hot_key_hash)]
        else:
            raise AssertionError("No key was specified.")

        anchor_args = []
        if anchor_url:
            if not anchor_data_hash:
                raise AssertionError("Anchor data hash is required when anchor URL is specified.")
            anchor_args = [
                "--anchor-url",
                str(anchor_url),
                "--anchor-data-hash",
                str(anchor_data_hash),
            ]

        self._clusterlib_obj.cli(
            [
                *self._group_args,
                "create",
                *vote_args,
                *gov_action_args,
                *key_args,
                *anchor_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def view(self, vote_file: itp.FileType) -> dict:
        """View a governance action vote."""
        vote_file = pl.Path(vote_file).expanduser()
        clusterlib_helpers._check_files_exist(vote_file, clusterlib_obj=self._clusterlib_obj)

        stdout = self._clusterlib_obj.cli(
            [
                *self._group_args,
                "view",
                "--vote-file",
                str(vote_file),
            ]
        ).stdout.strip()
        stdout_dec = stdout.decode("utf-8") if stdout else ""

        out: dict = json.loads(stdout_dec)
        return out
