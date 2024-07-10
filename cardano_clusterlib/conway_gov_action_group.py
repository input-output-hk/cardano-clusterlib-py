"""Group of methods for Conway governance action commands."""

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
            msg = "Either stake verification key or stake key hash must be set."
            raise AssertionError(msg)

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
            elif cc_member.cold_script_hash:
                cc_members_args.extend(
                    [
                        f"--{arg_action}-cc-cold-script-hash",
                        str(cc_member.cold_script_hash),
                    ]
                )
            else:
                msg = f"Either {arg_action} cold verification key or its hash must be set."
                raise AssertionError(msg)

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
                msg = "Previous action index must be set."
                raise AssertionError(msg)
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
        constitution_script_hash: str = "",
        deposit_return_stake_vkey: str = "",
        deposit_return_stake_vkey_file: tp.Optional[itp.FileType] = None,
        deposit_return_stake_key_hash: str = "",
        prev_action_txid: str = "",
        prev_action_ix: int = -1,
        destination_dir: itp.FileType = ".",
    ) -> structs.ActionConstitution:
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
        if constitution_script_hash:
            constitution_anchor_args.extend(
                [
                    "--constitution-script-hash",
                    str(constitution_script_hash),
                ]
            )

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

        action_out = structs.ActionConstitution(
            action_file=out_file,
            deposit_amt=deposit_amt,
            anchor_url=anchor_url,
            anchor_data_hash=anchor_data_hash,
            constitution_url=constitution_url,
            constitution_hash=constitution_hash,
            deposit_return_stake_vkey=deposit_return_stake_vkey,
            deposit_return_stake_vkey_file=helpers._maybe_path(file=deposit_return_stake_vkey_file),
            deposit_return_stake_key_hash=deposit_return_stake_key_hash,
            prev_action_txid=prev_action_txid,
            prev_action_ix=prev_action_ix,
        )

        return action_out

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
    ) -> structs.ActionInfo:
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

        action_out = structs.ActionInfo(
            action_file=out_file,
            deposit_amt=deposit_amt,
            anchor_url=anchor_url,
            anchor_data_hash=anchor_data_hash,
            deposit_return_stake_vkey=deposit_return_stake_vkey,
            deposit_return_stake_vkey_file=helpers._maybe_path(deposit_return_stake_vkey_file),
            deposit_return_stake_key_hash=deposit_return_stake_key_hash,
        )
        return action_out

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
    ) -> structs.ActionNoConfidence:
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

        action_out = structs.ActionNoConfidence(
            action_file=out_file,
            deposit_amt=deposit_amt,
            anchor_url=anchor_url,
            anchor_data_hash=anchor_data_hash,
            prev_action_txid=prev_action_txid,
            prev_action_ix=prev_action_ix,
            deposit_return_stake_vkey=deposit_return_stake_vkey,
            deposit_return_stake_vkey_file=helpers._maybe_path(deposit_return_stake_vkey_file),
            deposit_return_stake_key_hash=deposit_return_stake_key_hash,
        )
        return action_out

    def update_committee(
        self,
        action_name: str,
        deposit_amt: int,
        anchor_url: str,
        anchor_data_hash: str,
        threshold: str,
        add_cc_members: tp.Optional[tp.List[structs.CCMember]] = None,
        rem_cc_members: tp.Optional[tp.List[structs.CCMember]] = None,
        prev_action_txid: str = "",
        prev_action_ix: int = -1,
        deposit_return_stake_vkey: str = "",
        deposit_return_stake_vkey_file: tp.Optional[itp.FileType] = None,
        deposit_return_stake_key_hash: str = "",
        destination_dir: itp.FileType = ".",
    ) -> structs.ActionUpdateCommittee:
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
                "--threshold",
                threshold,
                "--out-file",
                str(out_file),
            ]
        )
        helpers._check_outfiles(out_file)

        action_out = structs.ActionUpdateCommittee(
            action_file=out_file,
            deposit_amt=deposit_amt,
            anchor_url=anchor_url,
            anchor_data_hash=anchor_data_hash,
            threshold=threshold,
            add_cc_members=add_cc_members or [],
            rem_cc_members=rem_cc_members or [],
            prev_action_txid=prev_action_txid,
            prev_action_ix=prev_action_ix,
            deposit_return_stake_vkey=deposit_return_stake_vkey,
            deposit_return_stake_vkey_file=helpers._maybe_path(deposit_return_stake_vkey_file),
            deposit_return_stake_key_hash=deposit_return_stake_key_hash,
        )
        return action_out

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
    ) -> structs.ActionPParamsUpdate:
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

        action_out = structs.ActionPParamsUpdate(
            action_file=out_file,
            deposit_amt=deposit_amt,
            anchor_url=anchor_url,
            anchor_data_hash=anchor_data_hash,
            cli_args=cli_args,
            prev_action_txid=prev_action_txid,
            prev_action_ix=prev_action_ix,
            deposit_return_stake_vkey=deposit_return_stake_vkey,
            deposit_return_stake_vkey_file=helpers._maybe_path(deposit_return_stake_vkey_file),
            deposit_return_stake_key_hash=deposit_return_stake_key_hash,
        )
        return action_out

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
    ) -> structs.ActionTreasuryWithdrawal:
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
            msg = "Either stake verification key or stake key hash must be set."
            raise AssertionError(msg)

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

        action_out = structs.ActionTreasuryWithdrawal(
            action_file=out_file,
            transfer_amt=transfer_amt,
            deposit_amt=deposit_amt,
            anchor_url=anchor_url,
            anchor_data_hash=anchor_data_hash,
            funds_receiving_stake_vkey=funds_receiving_stake_vkey,
            funds_receiving_stake_vkey_file=helpers._maybe_path(funds_receiving_stake_vkey_file),
            funds_receiving_stake_key_hash=funds_receiving_stake_key_hash,
            deposit_return_stake_vkey=deposit_return_stake_vkey,
            deposit_return_stake_vkey_file=helpers._maybe_path(deposit_return_stake_vkey_file),
            deposit_return_stake_key_hash=deposit_return_stake_key_hash,
        )
        return action_out

    def view(self, action_file: itp.FileType) -> tp.Dict[str, tp.Any]:
        """View a governance action vote."""
        action_file = pl.Path(action_file).expanduser()
        clusterlib_helpers._check_files_exist(action_file, clusterlib_obj=self._clusterlib_obj)

        stdout = self._clusterlib_obj.cli(
            [
                *self._group_args,
                "view",
                "--action-file",
                str(action_file),
            ]
        ).stdout.strip()
        stdout_dec = stdout.decode("utf-8") if stdout else ""

        out: tp.Dict[str, tp.Any] = json.loads(stdout_dec)
        return out

    def create_hardfork(
        self,
        action_name: str,
        deposit_amt: int,
        anchor_url: str,
        anchor_data_hash: str,
        protocol_major_version: int,
        protocol_minor_version: int,
        prev_action_txid: str = "",
        prev_action_ix: int = -1,
        deposit_return_stake_vkey: str = "",
        deposit_return_stake_vkey_file: tp.Optional[itp.FileType] = None,
        deposit_return_stake_key_hash: str = "",
        destination_dir: itp.FileType = ".",
    ) -> structs.ActionHardfork:
        """Create a hardfork initiation proposal."""
        # pylint: disable=too-many-arguments
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{action_name}_hardfork.action"
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
                "cardano-cli",
                "conway",
                *self._group_args,
                "create-hardfork",
                *self.magic_args,
                "--governance-action-deposit",
                str(deposit_amt),
                *key_args,
                *prev_action_args,
                *anchor_args,
                "--protocol-major-version",
                str(protocol_major_version),
                "--protocol-minor-version",
                str(protocol_minor_version),
                "--out-file",
                str(out_file),
            ],
            add_default_args=False,
        )
        helpers._check_outfiles(out_file)

        action_out = structs.ActionHardfork(
            action_file=out_file,
            deposit_amt=deposit_amt,
            anchor_url=anchor_url,
            anchor_data_hash=anchor_data_hash,
            protocol_major_version=protocol_major_version,
            protocol_minor_version=protocol_minor_version,
            prev_action_txid=prev_action_txid,
            prev_action_ix=prev_action_ix,
            deposit_return_stake_vkey=deposit_return_stake_vkey,
            deposit_return_stake_vkey_file=helpers._maybe_path(deposit_return_stake_vkey_file),
            deposit_return_stake_key_hash=deposit_return_stake_key_hash,
        )
        return action_out
