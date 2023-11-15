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

    def _get_key_args(
        self,
        drep_vkey: str = "",
        drep_vkey_file: tp.Optional[itp.FileType] = None,
        drep_key_hash: str = "",
        stake_pool_vkey: str = "",
        cold_vkey_file: tp.Optional[itp.FileType] = None,
        stake_pool_id: str = "",
    ) -> tp.List[str]:
        """Get arguments for verification key."""
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
        else:
            raise AssertionError("Either DRep hot key or stake pool id must be set.")

        return key_args

    def _get_cc_key_args(
        self,
        cc_hot_vkey: str = "",
        cc_hot_vkey_file: tp.Optional[itp.FileType] = None,
        cc_hot_key_hash: str = "",
    ) -> tp.List[str]:
        """Get arguments for verification key."""
        if cc_hot_vkey:
            key_args = ["--drep-verification-key", str(cc_hot_vkey)]
        elif cc_hot_vkey_file:
            key_args = ["--drep-verification-key-file", str(cc_hot_vkey_file)]
        elif cc_hot_key_hash:
            key_args = ["--drep-key-hash", str(cc_hot_key_hash)]
        else:
            raise AssertionError("Either Constitutional Committee hot key or its hash must be set.")

        return key_args

    def _get_vote_anchor_args(
        self,
        vote_anchor_url: str,
        vote_anchor_metadata: str = "",
        vote_anchor_metadata_file: tp.Optional[itp.FileType] = None,
        vote_anchor_metadata_hash: str = "",
    ) -> tp.List[str]:
        """Get arguments for vote anchor."""
        vote_anchor_args = ["--vote-anchor-url", str(vote_anchor_url)]
        if vote_anchor_metadata:
            vote_anchor_args.extend(["--vote-anchor-metadata", str(vote_anchor_metadata)])
        elif vote_anchor_metadata_file:
            vote_anchor_args.extend(
                [
                    "--vote-anchor-metadata-file",
                    str(vote_anchor_metadata_file),
                ]
            )
        elif vote_anchor_metadata_hash:
            vote_anchor_args.extend(
                [
                    "--vote-anchor-metadata-hash",
                    str(vote_anchor_metadata_hash),
                ]
            )
        else:
            raise AssertionError("Either vote anchor metadata or its hash must be set.")

        return vote_anchor_args

    def create(
        self,
        vote_name: str,
        action_txid: str,
        action_ix: int,
        vote_anchor_url: str,
        drep_vkey: str = "",
        drep_vkey_file: tp.Optional[itp.FileType] = None,
        drep_key_hash: str = "",
        stake_pool_vkey: str = "",
        cold_vkey_file: tp.Optional[itp.FileType] = None,
        stake_pool_id: str = "",
        cc_hot_vkey: str = "",
        cc_hot_vkey_file: tp.Optional[itp.FileType] = None,
        cc_hot_key_hash: str = "",
        vote_anchor_metadata: str = "",
        vote_anchor_metadata_file: tp.Optional[itp.FileType] = None,
        vote_anchor_metadata_hash: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Create a governance action vote."""
        # pylint: disable=too-many-arguments
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{vote_name}.vote"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        gov_action_args = [
            "--governance-action-tx-id",
            str(action_txid),
            "--governance-action-index",
            str(action_ix),
        ]

        key_args = self._get_key_args(
            drep_vkey=drep_vkey,
            drep_vkey_file=drep_vkey_file,
            drep_key_hash=drep_key_hash,
            stake_pool_vkey=stake_pool_vkey,
            cold_vkey_file=cold_vkey_file,
            stake_pool_id=stake_pool_id,
        )

        cc_key_args = self._get_cc_key_args(
            cc_hot_vkey=cc_hot_vkey,
            cc_hot_vkey_file=cc_hot_vkey_file,
            cc_hot_key_hash=cc_hot_key_hash,
        )

        vote_anchor_args = self._get_vote_anchor_args(
            vote_anchor_url=vote_anchor_url,
            vote_anchor_metadata=vote_anchor_metadata,
            vote_anchor_metadata_file=vote_anchor_metadata_file,
            vote_anchor_metadata_hash=vote_anchor_metadata_hash,
        )

        self._clusterlib_obj.cli(
            [
                *self._group_args,
                "create",
                *key_args,
                *gov_action_args,
                *key_args,
                *cc_key_args,
                *vote_anchor_args,
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
