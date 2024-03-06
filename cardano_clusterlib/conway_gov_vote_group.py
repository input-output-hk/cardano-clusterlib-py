"""Group of methods for Conway governance vote commands."""

import json
import logging
import pathlib as pl
import typing as tp

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import consts
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
from cardano_clusterlib import types as itp

LOGGER = logging.getLogger(__name__)


class ConwayGovVoteGroup:
    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj
        self._group_args = ("governance", "vote")

    def _get_vote_args(
        self,
        vote: consts.Votes,
    ) -> tp.List[str]:
        if vote == consts.Votes.YES:
            vote_args = ["--yes"]
        elif vote == consts.Votes.NO:
            vote_args = ["--no"]
        elif vote == consts.Votes.ABSTAIN:
            vote_args = ["--abstain"]
        else:
            msg = "No vote was specified."
            raise AssertionError(msg)

        return vote_args

    def _get_gov_action_args(
        self,
        action_txid: str,
        action_ix: int,
    ) -> tp.List[str]:
        gov_action_args = [
            "--governance-action-tx-id",
            str(action_txid),
            "--governance-action-index",
            str(action_ix),
        ]
        return gov_action_args

    def _get_anchor_args(
        self,
        anchor_url: str = "",
        anchor_data_hash: str = "",
    ) -> tp.List[str]:
        anchor_args = []
        if anchor_url:
            if not anchor_data_hash:
                msg = "Anchor data hash is required when anchor URL is specified."
                raise AssertionError(msg)
            anchor_args = [
                "--anchor-url",
                str(anchor_url),
                "--anchor-data-hash",
                str(anchor_data_hash),
            ]
        return anchor_args

    def create_committee(
        self,
        vote_name: str,
        action_txid: str,
        action_ix: int,
        vote: consts.Votes,
        cc_hot_vkey: str = "",
        cc_hot_vkey_file: tp.Optional[itp.FileType] = None,
        cc_hot_key_hash: str = "",
        anchor_url: str = "",
        anchor_data_hash: str = "",
        destination_dir: itp.FileType = ".",
    ) -> structs.VoteCC:
        """Create a governance action vote for a commitee member."""
        # pylint: disable=too-many-arguments
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{vote_name}_cc.vote"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        vote_args = self._get_vote_args(vote=vote)
        gov_action_args = self._get_gov_action_args(action_txid=action_txid, action_ix=action_ix)
        anchor_args = self._get_anchor_args(
            anchor_url=anchor_url, anchor_data_hash=anchor_data_hash
        )

        if cc_hot_vkey:
            key_args = ["--cc-hot-verification-key", cc_hot_vkey]
        elif cc_hot_vkey_file:
            key_args = ["--cc-hot-verification-key-file", str(cc_hot_vkey_file)]
        elif cc_hot_key_hash:
            key_args = ["--cc-hot-key-hash", cc_hot_key_hash]
        else:
            msg = "No CC key was specified."
            raise AssertionError(msg)

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

        vote_cc = structs.VoteCC(
            action_txid=action_txid,
            action_ix=action_ix,
            vote=vote,
            vote_file=out_file,
            cc_hot_vkey=cc_hot_vkey,
            cc_hot_vkey_file=helpers._maybe_path(cc_hot_vkey_file),
            cc_hot_key_hash=cc_hot_key_hash,
            anchor_url=anchor_url,
            anchor_data_hash=anchor_data_hash,
        )
        return vote_cc

    def create_drep(
        self,
        vote_name: str,
        action_txid: str,
        action_ix: int,
        vote: consts.Votes,
        drep_vkey: str = "",
        drep_vkey_file: tp.Optional[itp.FileType] = None,
        drep_key_hash: str = "",
        anchor_url: str = "",
        anchor_data_hash: str = "",
        destination_dir: itp.FileType = ".",
    ) -> structs.VoteDrep:
        """Create a governance action vote for a DRep."""
        # pylint: disable=too-many-arguments
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{vote_name}_drep.vote"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        vote_args = self._get_vote_args(vote=vote)
        gov_action_args = self._get_gov_action_args(action_txid=action_txid, action_ix=action_ix)
        anchor_args = self._get_anchor_args(
            anchor_url=anchor_url, anchor_data_hash=anchor_data_hash
        )

        if drep_vkey:
            key_args = ["--drep-verification-key", drep_vkey]
        elif drep_vkey_file:
            key_args = ["--drep-verification-key-file", str(drep_vkey_file)]
        elif drep_key_hash:
            key_args = ["--drep-key-hash", drep_key_hash]
        else:
            msg = "No DRep key was specified."
            raise AssertionError(msg)

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

        vote_drep = structs.VoteDrep(
            action_txid=action_txid,
            action_ix=action_ix,
            vote=vote,
            vote_file=out_file,
            drep_vkey=drep_vkey,
            drep_vkey_file=helpers._maybe_path(drep_vkey_file),
            drep_key_hash=drep_key_hash,
            anchor_url=anchor_url,
            anchor_data_hash=anchor_data_hash,
        )
        return vote_drep

    def create_spo(
        self,
        vote_name: str,
        action_txid: str,
        action_ix: int,
        vote: consts.Votes,
        stake_pool_vkey: str = "",
        cold_vkey_file: tp.Optional[itp.FileType] = None,
        stake_pool_id: str = "",
        anchor_url: str = "",
        anchor_data_hash: str = "",
        destination_dir: itp.FileType = ".",
    ) -> structs.VoteSPO:
        """Create a governance action vote for an SPO."""
        # pylint: disable=too-many-arguments
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{vote_name}_spo.vote"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        vote_args = self._get_vote_args(vote=vote)
        gov_action_args = self._get_gov_action_args(action_txid=action_txid, action_ix=action_ix)
        anchor_args = self._get_anchor_args(
            anchor_url=anchor_url, anchor_data_hash=anchor_data_hash
        )

        if stake_pool_vkey:
            key_args = ["--stake-pool-verification-key", stake_pool_vkey]
        elif cold_vkey_file:
            key_args = ["--cold-verification-key-file", str(cold_vkey_file)]
        elif stake_pool_id:
            key_args = ["--stake-pool-id", stake_pool_id]
        else:
            msg = "No key was specified."
            raise AssertionError(msg)

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

        vote_drep = structs.VoteSPO(
            action_txid=action_txid,
            action_ix=action_ix,
            vote=vote,
            stake_pool_vkey=stake_pool_vkey,
            cold_vkey_file=helpers._maybe_path(cold_vkey_file),
            stake_pool_id=stake_pool_id,
            vote_file=out_file,
            anchor_url=anchor_url,
            anchor_data_hash=anchor_data_hash,
        )
        return vote_drep

    def view(self, vote_file: itp.FileType) -> tp.Dict[str, tp.Any]:
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

        out: tp.Dict[str, tp.Any] = json.loads(stdout_dec)
        return out
