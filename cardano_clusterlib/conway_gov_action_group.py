"""Group of methods for Conway governance action commands."""
import logging
import pathlib as pl
import typing as tp

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import consts
from cardano_clusterlib import helpers
from cardano_clusterlib import types as itp


LOGGER = logging.getLogger(__name__)


class ConwayGovActionGroup:
    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj
        self._group_args = ("governance", "action")

        if self._clusterlib_obj.network_magic == consts.MAINNET_MAGIC:
            self.magic_args = ["--mainnet"]
        else:
            self.magic_args = ["--testnet"]

    def _get_key_args(
        self,
        stake_vkey: str = "",
        stake_vkey_file: tp.Optional[itp.FileType] = None,
        stake_key_hash: str = "",
    ) -> tp.List[str]:
        """Get arguments for verification key."""
        if stake_vkey:
            key_args = ["--stake-verification-key", str(stake_vkey)]
        elif stake_vkey_file:
            key_args = ["--stake-verification-key-file", str(stake_vkey_file)]
        elif stake_key_hash:
            key_args = ["--stake-key-hash", str(stake_key_hash)]
        else:
            raise AssertionError("Either stake verification key or stake key hash must be set.")

        return key_args

    def _get_proposal_anchor_args(
        self,
        proposal_anchor_url: str,
        proposal_anchor_metadata: str = "",
        proposal_anchor_metadata_file: tp.Optional[itp.FileType] = None,
        proposal_anchor_metadata_hash: str = "",
    ) -> tp.List[str]:
        """Get arguments for proposal anchor."""
        proposal_anchor_args = ["--proposal-anchor-url", str(proposal_anchor_url)]
        if proposal_anchor_metadata:
            proposal_anchor_args.extend(
                ["--proposal-anchor-metadata", str(proposal_anchor_metadata)]
            )
        elif proposal_anchor_metadata_file:
            proposal_anchor_args.extend(
                [
                    "--proposal-anchor-metadata-file",
                    str(proposal_anchor_metadata_file),
                ]
            )
        elif proposal_anchor_metadata_hash:
            proposal_anchor_args.extend(
                [
                    "--proposal-anchor-metadata-hash",
                    str(proposal_anchor_metadata_hash),
                ]
            )
        else:
            raise AssertionError("Either proposal anchor metadata or its hash must be set.")

        return proposal_anchor_args

    def create_constitution(
        self,
        action_name: str,
        deposit_amt: int,
        proposal_anchor_url: str,
        constitution_anchor_url: str,
        stake_vkey: str = "",
        stake_vkey_file: tp.Optional[itp.FileType] = None,
        stake_key_hash: str = "",
        prev_action_txid: str = "",
        prev_action_ix: str = "",
        proposal_anchor_metadata: str = "",
        proposal_anchor_metadata_file: tp.Optional[itp.FileType] = None,
        proposal_anchor_metadata_hash: str = "",
        constitution_anchor_metadata: str = "",
        constitution_anchor_metadata_file: tp.Optional[itp.FileType] = None,
        constitution_anchor_metadata_hash: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Create a constitution."""
        # pylint: disable=too-many-arguments
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{action_name}_constitution.action"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        key_args = self._get_key_args(
            stake_vkey=stake_vkey,
            stake_vkey_file=stake_vkey_file,
            stake_key_hash=stake_key_hash,
        )

        proposal_anchor_args = self._get_proposal_anchor_args(
            proposal_anchor_url=proposal_anchor_url,
            proposal_anchor_metadata=proposal_anchor_metadata,
            proposal_anchor_metadata_file=proposal_anchor_metadata_file,
            proposal_anchor_metadata_hash=proposal_anchor_metadata_hash,
        )

        prev_action_args = []
        if prev_action_txid:
            if not prev_action_ix:
                raise AssertionError("Previous action index must be set.")
            prev_action_args = [
                "--governance-action-tx-id",
                str(prev_action_txid),
                "--governance-action-index",
                str(prev_action_ix),
            ]

        constitution_anchor_args = ["--constitution-anchor-url", str(constitution_anchor_url)]
        if constitution_anchor_metadata:
            constitution_anchor_args.extend(
                ["--constitution-anchor-metadata", str(constitution_anchor_metadata)]
            )
        elif constitution_anchor_metadata_file:
            constitution_anchor_args.extend(
                [
                    "--constitution-anchor-metadata-file",
                    str(constitution_anchor_metadata_file),
                ]
            )
        elif constitution_anchor_metadata_hash:
            constitution_anchor_args.extend(
                [
                    "--constitution-anchor-metadata-hash",
                    str(constitution_anchor_metadata_hash),
                ]
            )
        else:
            raise AssertionError("Either constitution anchor metadata or its hash must be set.")

        self._clusterlib_obj.cli(
            [
                *self._group_args,
                "create-constitution",
                *self.magic_args,
                "--governance-action-deposit",
                str(deposit_amt),
                *key_args,
                *prev_action_args,
                *proposal_anchor_args,
                *constitution_anchor_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def create_info(
        self,
        action_name: str,
        deposit_amt: int,
        proposal_anchor_url: str,
        stake_vkey: str = "",
        stake_vkey_file: tp.Optional[itp.FileType] = None,
        stake_key_hash: str = "",
        proposal_anchor_metadata: str = "",
        proposal_anchor_metadata_file: tp.Optional[itp.FileType] = None,
        proposal_anchor_metadata_hash: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Create an info action."""
        # pylint: disable=too-many-arguments
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{action_name}_info.action"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        key_args = self._get_key_args(
            stake_vkey=stake_vkey,
            stake_vkey_file=stake_vkey_file,
            stake_key_hash=stake_key_hash,
        )

        proposal_anchor_args = self._get_proposal_anchor_args(
            proposal_anchor_url=proposal_anchor_url,
            proposal_anchor_metadata=proposal_anchor_metadata,
            proposal_anchor_metadata_file=proposal_anchor_metadata_file,
            proposal_anchor_metadata_hash=proposal_anchor_metadata_hash,
        )

        self._clusterlib_obj.cli(
            [
                *self._group_args,
                "create-info",
                *self.magic_args,
                "--governance-action-deposit",
                str(deposit_amt),
                *key_args,
                *proposal_anchor_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def create_no_confidence(
        self,
        action_name: str,
        deposit_amt: int,
        proposal_anchor_url: str,
        prev_action_txid: str,
        prev_action_ix: str,
        stake_vkey: str = "",
        stake_vkey_file: tp.Optional[itp.FileType] = None,
        stake_key_hash: str = "",
        proposal_anchor_metadata: str = "",
        proposal_anchor_metadata_file: tp.Optional[itp.FileType] = None,
        proposal_anchor_metadata_hash: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Create a no confidence proposal."""
        # pylint: disable=too-many-arguments
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{action_name}_confidence.action"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        key_args = self._get_key_args(
            stake_vkey=stake_vkey,
            stake_vkey_file=stake_vkey_file,
            stake_key_hash=stake_key_hash,
        )

        proposal_anchor_args = self._get_proposal_anchor_args(
            proposal_anchor_url=proposal_anchor_url,
            proposal_anchor_metadata=proposal_anchor_metadata,
            proposal_anchor_metadata_file=proposal_anchor_metadata_file,
            proposal_anchor_metadata_hash=proposal_anchor_metadata_hash,
        )

        prev_action_args = [
            "--governance-action-tx-id",
            str(prev_action_txid),
            "--governance-action-index",
            str(prev_action_ix),
        ]

        self._clusterlib_obj.cli(
            [
                *self._group_args,
                "create-no-confidence",
                *self.magic_args,
                "--governance-action-deposit",
                str(deposit_amt),
                *key_args,
                *prev_action_args,
                *proposal_anchor_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file
