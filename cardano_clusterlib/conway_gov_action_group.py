"""Group of methods for Conway governance action commands."""
import logging
import pathlib as pl
import typing as tp

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import consts
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
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

    def _get_deposit_return_key_args(
        self,
        deposit_return_stake_vkey: str = "",
        deposit_return_stake_vkey_file: tp.Optional[itp.FileType] = None,
        deposit_return_stake_key_hash: str = "",
    ) -> tp.List[str]:
        """Get arguments for verification key."""
        if deposit_return_stake_vkey:
            key_args = ["--deposit-return-stake-verification-key", str(deposit_return_stake_vkey)]
        elif deposit_return_stake_vkey_file:
            key_args = [
                "--deposit-return-stake-verification-key-file",
                str(deposit_return_stake_vkey_file),
            ]
        elif deposit_return_stake_key_hash:
            key_args = ["--deposit-return-stake-key-hash", str(deposit_return_stake_key_hash)]
        else:
            raise AssertionError("Either stake verification key or stake key hash must be set.")

        return key_args

    def _get_cc_members_args(
        self,
        cc_members: tp.List[structs.CCMember],
        remove: bool = False,
    ) -> tp.List[str]:
        """Get arguments for committee members."""
        arg_action = "remove" if remove else "add"
        cc_members_args = []

        for cc_member in cc_members:
            if cc_member.cold_vkey:
                cc_members_args.extend(
                    [
                        f"--{arg_action}-cc-cold-verification-key",
                        str(cc_member.cold_vkey),
                    ]
                )
            elif cc_member.cold_vkey_file:
                cc_members_args.extend(
                    [
                        f"--{arg_action}-cc-cold-verification-key-file",
                        str(cc_member.cold_vkey_file),
                    ]
                )
            elif cc_member.cold_vkey_hash:
                cc_members_args.extend(
                    [
                        f"--{arg_action}-cc-cold-verification-key-hash",
                        str(cc_member.cold_vkey_hash),
                    ]
                )
            else:
                raise AssertionError(
                    f"Either {arg_action} cold verification key or its hash must be set."
                )

            if not remove:
                cc_members_args.extend(["--epoch", str(cc_member.epoch)])

        return cc_members_args

    def _get_optional_prev_action_args(
        self,
        prev_action_txid: str = "",
        prev_action_ix: int = -1,
    ) -> tp.List[str]:
        """Get arguments for previous action."""
        prev_action_args = []
        if prev_action_txid:
            if prev_action_ix == -1:
                raise AssertionError("Previous action index must be set.")
            prev_action_args = [
                "--prev-governance-action-tx-id",
                str(prev_action_txid),
                "--prev-governance-action-index",
                str(prev_action_ix),
            ]

        return prev_action_args

    def _get_anchor_args(
        self,
        anchor_url: str,
        anchor_data_hash: str = "",
    ) -> tp.List[str]:
        """Get arguments for anchor."""
        anchor_args = [
            "--anchor-url",
            str(anchor_url),
            "--anchor-data-hash",
            str(anchor_data_hash),
        ]

        return anchor_args

    def create_constitution(
        self,
        action_name: str,
        deposit_amt: int,
        anchor_url: str,
        anchor_data_hash: str,
        constitution_url: str,
        constitution_hash: str,
        deposit_return_stake_vkey: str = "",
        deposit_return_stake_vkey_file: tp.Optional[itp.FileType] = None,
        deposit_return_stake_key_hash: str = "",
        prev_action_txid: str = "",
        prev_action_ix: int = -1,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Create a constitution."""
        # pylint: disable=too-many-arguments
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{action_name}_constitution.action"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        key_args = self._get_deposit_return_key_args(
            deposit_return_stake_vkey=deposit_return_stake_vkey,
            deposit_return_stake_vkey_file=deposit_return_stake_vkey_file,
            deposit_return_stake_key_hash=deposit_return_stake_key_hash,
        )

        anchor_args = self._get_anchor_args(
            anchor_url=anchor_url,
            anchor_data_hash=anchor_data_hash,
        )

        prev_action_args = self._get_optional_prev_action_args(
            prev_action_txid=prev_action_txid, prev_action_ix=prev_action_ix
        )

        constitution_anchor_args = [
            "--constitution-url",
            str(constitution_url),
            "--constitution-hash",
            str(constitution_hash),
        ]

        self._clusterlib_obj.cli(
            [
                *self._group_args,
                "create-constitution",
                *self.magic_args,
                "--governance-action-deposit",
                str(deposit_amt),
                *key_args,
                *prev_action_args,
                *anchor_args,
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
        anchor_url: str,
        anchor_data_hash: str,
        deposit_return_stake_vkey: str = "",
        deposit_return_stake_vkey_file: tp.Optional[itp.FileType] = None,
        deposit_return_stake_key_hash: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Create an info action."""
        # pylint: disable=too-many-arguments
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{action_name}_info.action"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        key_args = self._get_deposit_return_key_args(
            deposit_return_stake_vkey=deposit_return_stake_vkey,
            deposit_return_stake_vkey_file=deposit_return_stake_vkey_file,
            deposit_return_stake_key_hash=deposit_return_stake_key_hash,
        )

        anchor_args = self._get_anchor_args(
            anchor_url=anchor_url,
            anchor_data_hash=anchor_data_hash,
        )

        self._clusterlib_obj.cli(
            [
                *self._group_args,
                "create-info",
                *self.magic_args,
                "--governance-action-deposit",
                str(deposit_amt),
                *key_args,
                *anchor_args,
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
        anchor_url: str,
        anchor_data_hash: str,
        prev_action_txid: str,
        prev_action_ix: int,
        deposit_return_stake_vkey: str = "",
        deposit_return_stake_vkey_file: tp.Optional[itp.FileType] = None,
        deposit_return_stake_key_hash: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Create a no confidence proposal."""
        # pylint: disable=too-many-arguments
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{action_name}_confidence.action"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        key_args = self._get_deposit_return_key_args(
            deposit_return_stake_vkey=deposit_return_stake_vkey,
            deposit_return_stake_vkey_file=deposit_return_stake_vkey_file,
            deposit_return_stake_key_hash=deposit_return_stake_key_hash,
        )

        anchor_args = self._get_anchor_args(
            anchor_url=anchor_url,
            anchor_data_hash=anchor_data_hash,
        )

        prev_action_args = [
            "--prev-governance-action-tx-id",
            str(prev_action_txid),
            "--prev-governance-action-index",
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
                *anchor_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def update_committee(
        self,
        action_name: str,
        deposit_amt: int,
        anchor_url: str,
        anchor_data_hash: str,
        quorum: str,
        add_cc_members: tp.Optional[tp.List[structs.CCMember]] = None,
        rem_cc_members: tp.Optional[tp.List[structs.CCMember]] = None,
        prev_action_txid: str = "",
        prev_action_ix: int = -1,
        deposit_return_stake_vkey: str = "",
        deposit_return_stake_vkey_file: tp.Optional[itp.FileType] = None,
        deposit_return_stake_key_hash: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Create or update a new committee proposal."""
        # pylint: disable=too-many-arguments
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{action_name}_update_committee.action"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        anchor_args = self._get_anchor_args(
            anchor_url=anchor_url,
            anchor_data_hash=anchor_data_hash,
        )

        key_args = self._get_deposit_return_key_args(
            deposit_return_stake_vkey=deposit_return_stake_vkey,
            deposit_return_stake_vkey_file=deposit_return_stake_vkey_file,
            deposit_return_stake_key_hash=deposit_return_stake_key_hash,
        )

        prev_action_args = self._get_optional_prev_action_args(
            prev_action_txid=prev_action_txid, prev_action_ix=prev_action_ix
        )

        rem_cc_members_args = self._get_cc_members_args(
            cc_members=rem_cc_members or [], remove=True
        )
        add_cc_members_args = self._get_cc_members_args(cc_members=add_cc_members or [])

        self._clusterlib_obj.cli(
            [
                *self._group_args,
                "update-committee",
                *self.magic_args,
                "--governance-action-deposit",
                str(deposit_amt),
                *key_args,
                *prev_action_args,
                *anchor_args,
                *rem_cc_members_args,
                *add_cc_members_args,
                "--quorum",
                quorum,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def create_pparams_update(
        self,
        action_name: str,
        deposit_amt: int,
        anchor_url: str,
        anchor_data_hash: str,
        cli_args: itp.UnpackableSequence,
        prev_action_txid: str = "",
        prev_action_ix: int = -1,
        deposit_return_stake_vkey: str = "",
        deposit_return_stake_vkey_file: tp.Optional[itp.FileType] = None,
        deposit_return_stake_key_hash: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Create a protocol parameters update proposal."""
        # pylint: disable=too-many-arguments
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{action_name}_pparams_update.action"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        key_args = self._get_deposit_return_key_args(
            deposit_return_stake_vkey=deposit_return_stake_vkey,
            deposit_return_stake_vkey_file=deposit_return_stake_vkey_file,
            deposit_return_stake_key_hash=deposit_return_stake_key_hash,
        )

        anchor_args = self._get_anchor_args(
            anchor_url=anchor_url,
            anchor_data_hash=anchor_data_hash,
        )

        prev_action_args = self._get_optional_prev_action_args(
            prev_action_txid=prev_action_txid, prev_action_ix=prev_action_ix
        )

        self._clusterlib_obj.cli(
            [
                *self._group_args,
                "create-protocol-parameters-update",
                *self.magic_args,
                "--governance-action-deposit",
                str(deposit_amt),
                *key_args,
                *prev_action_args,
                *anchor_args,
                *cli_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def create_treasury_withdrawal(
        self,
        action_name: str,
        transfer_amt: int,
        deposit_amt: int,
        anchor_url: str,
        anchor_data_hash: str,
        funds_receiving_stake_vkey: str = "",
        funds_receiving_stake_vkey_file: tp.Optional[itp.FileType] = None,
        funds_receiving_stake_key_hash: str = "",
        deposit_return_stake_vkey: str = "",
        deposit_return_stake_vkey_file: tp.Optional[itp.FileType] = None,
        deposit_return_stake_key_hash: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Create a treasury withdrawal."""
        # pylint: disable=too-many-arguments
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{action_name}_info.action"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        if funds_receiving_stake_vkey:
            funds_key_args = [
                "--funds-receiving-stake-verification-key",
                str(funds_receiving_stake_vkey),
            ]
        elif funds_receiving_stake_vkey_file:
            funds_key_args = [
                "--funds-receiving-stake-verification-key-file",
                str(funds_receiving_stake_vkey_file),
            ]
        elif funds_receiving_stake_key_hash:
            funds_key_args = [
                "--funds-receiving-stake-key-hash",
                str(funds_receiving_stake_key_hash),
            ]
        else:
            raise AssertionError("Either stake verification key or stake key hash must be set.")

        deposit_key_args = self._get_deposit_return_key_args(
            deposit_return_stake_vkey=deposit_return_stake_vkey,
            deposit_return_stake_vkey_file=deposit_return_stake_vkey_file,
            deposit_return_stake_key_hash=deposit_return_stake_key_hash,
        )

        anchor_args = self._get_anchor_args(
            anchor_url=anchor_url,
            anchor_data_hash=anchor_data_hash,
        )

        self._clusterlib_obj.cli(
            [
                *self._group_args,
                "create-treasury-withdrawal",
                *self.magic_args,
                "--governance-action-deposit",
                str(deposit_amt),
                *deposit_key_args,
                *anchor_args,
                *funds_key_args,
                "--transfer",
                str(transfer_amt),
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file
