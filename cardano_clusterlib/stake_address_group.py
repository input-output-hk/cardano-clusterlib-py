"""Group of methods for working with stake addresses."""

import logging
import pathlib as pl
import typing as tp

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import exceptions
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
from cardano_clusterlib import types as itp

LOGGER = logging.getLogger(__name__)


class StakeAddressGroup:
    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj

    def _get_stake_vkey_args(
        self,
        stake_vkey: str = "",
        stake_vkey_file: tp.Optional[itp.FileType] = None,
        stake_script_file: tp.Optional[itp.FileType] = None,
        stake_address: tp.Optional[str] = None,
    ) -> tp.List[str]:
        """Return CLI args for stake vkey."""
        if stake_vkey:
            stake_args = ["--stake-verification-key", stake_vkey]
        elif stake_vkey_file:
            stake_args = ["--stake-verification-key-file", str(stake_vkey_file)]
        elif stake_script_file:
            stake_args = ["--stake-script-file", str(stake_script_file)]
        elif stake_address:
            stake_args = ["--stake-address", stake_address]
        else:
            msg = "Either `stake_vkey_file`, `stake_script_file` or `stake_address` is needed."
            raise AssertionError(msg)

        return stake_args

    def _get_drep_args(
        self,
        drep_script_hash: str = "",
        drep_vkey: str = "",
        drep_vkey_file: tp.Optional[itp.FileType] = None,
        drep_key_hash: str = "",
        always_abstain: bool = False,
        always_no_confidence: bool = False,
    ) -> tp.List[str]:
        """Return CLI args for DRep identification."""
        if always_abstain:
            drep_args = ["--always-abstain"]
        elif always_no_confidence:
            drep_args = ["--always-no-confidence"]
        elif drep_script_hash:
            drep_args = ["--drep-script-hash", str(drep_script_hash)]
        elif drep_vkey:
            drep_args = ["--drep-verification-key", str(drep_vkey)]
        elif drep_vkey_file:
            drep_args = ["--drep-verification-key-file", str(drep_vkey_file)]
        elif drep_key_hash:
            drep_args = ["--drep-key-hash", str(drep_key_hash)]
        else:
            msg = "DRep identification, verification key or script hash is needed."
            raise AssertionError(msg)

        return drep_args

    def _get_pool_key_args(
        self,
        stake_pool_vkey: str = "",
        cold_vkey_file: tp.Optional[itp.FileType] = None,
        stake_pool_id: str = "",
    ) -> tp.List[str]:
        """Return CLI args for pool key."""
        if stake_pool_vkey:
            pool_key_args = ["--stake-pool-verification-key", stake_pool_vkey]
        elif cold_vkey_file:
            pool_key_args = ["--cold-verification-key-file", str(cold_vkey_file)]
        elif stake_pool_id:
            pool_key_args = ["--stake-pool-id", stake_pool_id]
        else:
            msg = "No stake pool key was specified."
            raise AssertionError(msg)

        return pool_key_args

    def gen_stake_addr(
        self,
        addr_name: str,
        stake_vkey_file: tp.Optional[itp.FileType] = None,
        stake_script_file: tp.Optional[itp.FileType] = None,
        destination_dir: itp.FileType = ".",
    ) -> str:
        """Generate a stake address.

        Args:
            addr_name: A name of payment address.
            stake_vkey_file: A path to corresponding stake vkey file (optional).
            stake_script_file: A path to corresponding payment script file (optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            str: A generated stake address.
        """
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{addr_name}_stake.addr"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        if stake_vkey_file:
            cli_args = ["--stake-verification-key-file", str(stake_vkey_file)]
        elif stake_script_file:
            cli_args = ["--stake-script-file", str(stake_script_file)]
        else:
            msg = "Either `stake_vkey_file` or `stake_script_file` is needed."
            raise AssertionError(msg)

        self._clusterlib_obj.cli(
            [
                "stake-address",
                "build",
                *cli_args,
                *self._clusterlib_obj.magic_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return helpers.read_address_from_file(out_file)

    def gen_stake_key_pair(
        self, key_name: str, destination_dir: itp.FileType = "."
    ) -> structs.KeyPair:
        """Generate a stake address key pair.

        Args:
            key_name: A name of the key pair.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            structs.KeyPair: A tuple containing the key pair.
        """
        destination_dir = pl.Path(destination_dir).expanduser()
        vkey = destination_dir / f"{key_name}_stake.vkey"
        skey = destination_dir / f"{key_name}_stake.skey"
        clusterlib_helpers._check_files_exist(vkey, skey, clusterlib_obj=self._clusterlib_obj)

        self._clusterlib_obj.cli(
            [
                "stake-address",
                "key-gen",
                "--verification-key-file",
                str(vkey),
                "--signing-key-file",
                str(skey),
            ]
        )

        helpers._check_outfiles(vkey, skey)
        return structs.KeyPair(vkey, skey)

    def gen_stake_addr_registration_cert(
        self,
        addr_name: str,
        deposit_amt: int = -1,
        stake_vkey: str = "",
        stake_vkey_file: tp.Optional[itp.FileType] = None,
        stake_script_file: tp.Optional[itp.FileType] = None,
        stake_address: tp.Optional[str] = None,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a stake address registration certificate.

        Args:
            addr_name: A name of stake address.
            deposit_amt: A stake address registration deposit amount (required in Conway+).
            stake_vkey: A stake vkey file (optional).
            stake_vkey_file: A path to corresponding stake vkey file (optional).
            stake_script_file: A path to corresponding stake script file (optional).
            stake_address: Stake address key, bech32 or hex-encoded (optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated certificate.
        """
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{addr_name}_stake_reg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        stake_args = self._get_stake_vkey_args(
            stake_vkey=stake_vkey,
            stake_vkey_file=stake_vkey_file,
            stake_script_file=stake_script_file,
            stake_address=stake_address,
        )

        deposit_args = [] if deposit_amt == -1 else ["--key-reg-deposit-amt", str(deposit_amt)]

        self._clusterlib_obj.cli(
            [
                "stake-address",
                "registration-certificate",
                *deposit_args,
                *stake_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def gen_stake_addr_deregistration_cert(
        self,
        addr_name: str,
        deposit_amt: int = -1,
        stake_vkey_file: tp.Optional[itp.FileType] = None,
        stake_script_file: tp.Optional[itp.FileType] = None,
        stake_address: tp.Optional[str] = None,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a stake address deregistration certificate.

        Args:
            addr_name: A name of stake address.
            deposit_amt: A stake address registration deposit amount (required in Conway+).
            stake_vkey_file: A path to corresponding stake vkey file (optional).
            stake_script_file: A path to corresponding stake script file (optional).
            stake_address: Stake address key, bech32 or hex-encoded (optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated certificate.
        """
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{addr_name}_stake_dereg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        stake_args = self._get_stake_vkey_args(
            stake_vkey_file=stake_vkey_file,
            stake_script_file=stake_script_file,
            stake_address=stake_address,
        )

        deposit_args = [] if deposit_amt == -1 else ["--key-reg-deposit-amt", str(deposit_amt)]

        self._clusterlib_obj.cli(
            [
                "stake-address",
                "deregistration-certificate",
                *deposit_args,
                *stake_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def gen_stake_addr_delegation_cert(
        self,
        addr_name: str,
        stake_vkey: str = "",
        stake_vkey_file: tp.Optional[itp.FileType] = None,
        stake_script_file: tp.Optional[itp.FileType] = None,
        stake_address: tp.Optional[str] = None,
        stake_pool_vkey: str = "",
        cold_vkey_file: tp.Optional[itp.FileType] = None,
        stake_pool_id: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a stake address delegation certificate.

        Args:
            addr_name: A name of stake address.
            stake_vkey: A stake vkey file (optional).
            stake_vkey_file: A path to corresponding stake vkey file (optional).
            stake_script_file: A path to corresponding stake script file (optional).
            stake_address: Stake address key, bech32 or hex-encoded (optional).
            stake_pool_vkey: A stake pool verification key (Bech32 or hex-encoded, optional).
            cold_vkey_file: A path to pool cold vkey file (optional).
            stake_pool_id: An ID of the stake pool (optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated certificate.
        """
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{addr_name}_stake_deleg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        command_name = "delegation-certificate"
        if self._clusterlib_obj.command_era:
            command_name = "stake-delegation-certificate"

        stake_key_args = self._get_stake_vkey_args(
            stake_vkey=stake_vkey,
            stake_vkey_file=stake_vkey_file,
            stake_script_file=stake_script_file,
            stake_address=stake_address,
        )
        pool_key_args = self._get_pool_key_args(
            stake_pool_vkey=stake_pool_vkey,
            cold_vkey_file=cold_vkey_file,
            stake_pool_id=stake_pool_id,
        )

        self._clusterlib_obj.cli(
            [
                "stake-address",
                command_name,
                *stake_key_args,
                *pool_key_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def gen_vote_delegation_cert(
        self,
        addr_name: str,
        stake_vkey: str = "",
        stake_vkey_file: tp.Optional[itp.FileType] = None,
        stake_script_file: tp.Optional[itp.FileType] = None,
        stake_address: tp.Optional[str] = None,
        drep_script_hash: str = "",
        drep_vkey: str = "",
        drep_vkey_file: tp.Optional[itp.FileType] = None,
        drep_key_hash: str = "",
        always_abstain: bool = False,
        always_no_confidence: bool = False,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a stake address vote delegation certificate.

        Args:
            addr_name: A name of stake address.
            stake_vkey: A stake vkey file (optional).
            stake_vkey_file: A path to corresponding stake vkey file (optional).
            stake_script_file: A path to corresponding stake script file (optional).
            stake_address: Stake address key, bech32 or hex-encoded (optional).
            drep_script_hash: DRep script hash (hex-encoded, optional).
            drep_vkey: DRep verification key (Bech32 or hex-encoded, optional).
            drep_vkey_file: Filepath of the DRep verification key (optional).
            drep_key_hash: DRep verification key hash
                (either Bech32-encoded or hex-encoded, optional).
            always_abstain: A bool indicating whether to delegate to always-abstain DRep (optional).
            always_no_confidence: A bool indicating whether to delegate to
                always-vote-no-confidence DRep (optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated certificate.
        """
        # pylint: disable=too-many-arguments
        if not self._clusterlib_obj.conway_genesis:
            msg = "Conway governance can be used only with Command era >= Conway."
            raise exceptions.CLIError(msg)

        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{addr_name}_vote_deleg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        stake_args = self._get_stake_vkey_args(
            stake_vkey=stake_vkey,
            stake_vkey_file=stake_vkey_file,
            stake_script_file=stake_script_file,
            stake_address=stake_address,
        )
        drep_args = self._get_drep_args(
            drep_script_hash=drep_script_hash,
            drep_vkey=drep_vkey,
            drep_vkey_file=drep_vkey_file,
            drep_key_hash=drep_key_hash,
            always_abstain=always_abstain,
            always_no_confidence=always_no_confidence,
        )

        self._clusterlib_obj.cli(
            [
                "stake-address",
                "vote-delegation-certificate",
                *stake_args,
                *drep_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def gen_stake_and_vote_delegation_cert(
        self,
        addr_name: str,
        stake_vkey: str = "",
        stake_vkey_file: tp.Optional[itp.FileType] = None,
        stake_script_file: tp.Optional[itp.FileType] = None,
        stake_address: tp.Optional[str] = None,
        stake_pool_vkey: str = "",
        cold_vkey_file: tp.Optional[itp.FileType] = None,
        stake_pool_id: str = "",
        drep_script_hash: str = "",
        drep_vkey: str = "",
        drep_vkey_file: tp.Optional[itp.FileType] = None,
        drep_key_hash: str = "",
        always_abstain: bool = False,
        always_no_confidence: bool = False,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a stake address stake and vote delegation certificate.

        Args:
            addr_name: A name of stake address.
            stake_vkey: A stake vkey file (optional).
            stake_vkey_file: A path to corresponding stake vkey file (optional).
            stake_script_file: A path to corresponding stake script file (optional).
            stake_address: Stake address key, bech32 or hex-encoded (optional).
            stake_pool_vkey: A stake pool verification key (Bech32 or hex-encoded, optional).
            cold_vkey_file: A path to pool cold vkey file (optional).
            stake_pool_id: An ID of the stake pool (optional).
                (either Bech32-encoded or hex-encoded, optional).
            drep_script_hash: DRep script hash (hex-encoded, optional).
            drep_vkey: DRep verification key (Bech32 or hex-encoded, optional).
            drep_vkey_file: Filepath of the DRep verification key (optional).
            drep_key_hash: DRep verification key hash
            always_abstain: A bool indicating whether to delegate to always-abstain DRep (optional).
            always_no_confidence: A bool indicating whether to delegate to
                always-vote-no-confidence DRep (optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated certificate.
        """
        # pylint: disable=too-many-arguments
        if not self._clusterlib_obj.conway_genesis:
            msg = "Conway governance can be used only with Command era >= Conway."
            raise exceptions.CLIError(msg)

        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{addr_name}_vote_deleg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        stake_key_args = self._get_stake_vkey_args(
            stake_vkey=stake_vkey,
            stake_vkey_file=stake_vkey_file,
            stake_script_file=stake_script_file,
            stake_address=stake_address,
        )
        pool_key_args = self._get_pool_key_args(
            stake_pool_vkey=stake_pool_vkey,
            cold_vkey_file=cold_vkey_file,
            stake_pool_id=stake_pool_id,
        )
        drep_args = self._get_drep_args(
            drep_script_hash=drep_script_hash,
            drep_vkey=drep_vkey,
            drep_vkey_file=drep_vkey_file,
            drep_key_hash=drep_key_hash,
            always_abstain=always_abstain,
            always_no_confidence=always_no_confidence,
        )

        self._clusterlib_obj.cli(
            [
                "stake-address",
                "stake-and-vote-delegation-certificate",
                *stake_key_args,
                *pool_key_args,
                *drep_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def gen_stake_addr_and_keys(
        self, name: str, destination_dir: itp.FileType = "."
    ) -> structs.AddressRecord:
        """Generate stake address and key pair.

        Args:
            name: A name of the address and key pair.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            structs.AddressRecord: A tuple containing the address and key pair / script file.
        """
        key_pair = self.gen_stake_key_pair(key_name=name, destination_dir=destination_dir)
        addr = self.gen_stake_addr(
            addr_name=name, stake_vkey_file=key_pair.vkey_file, destination_dir=destination_dir
        )

        return structs.AddressRecord(
            address=addr, vkey_file=key_pair.vkey_file, skey_file=key_pair.skey_file
        )

    def get_stake_vkey_hash(
        self,
        stake_vkey_file: tp.Optional[itp.FileType] = None,
        stake_vkey: tp.Optional[str] = None,
    ) -> str:
        """Return the hash of a stake address key.

        Args:
            stake_vkey_file: A path to stake vkey file (optional).
            stake_vkey: A stake vkey (Bech32, optional).

        Returns:
            str: A generated hash.
        """
        if stake_vkey:
            cli_args = ["--stake-verification-key", stake_vkey]
        elif stake_vkey_file:
            cli_args = ["--stake-verification-key-file", str(stake_vkey_file)]
        else:
            msg = "Either `stake_vkey` or `stake_vkey_file` is needed."
            raise AssertionError(msg)

        return (
            self._clusterlib_obj.cli(["stake-address", "key-hash", *cli_args])
            .stdout.rstrip()
            .decode("ascii")
        )

    def withdraw_reward(
        self,
        stake_addr_record: structs.AddressRecord,
        dst_addr_record: structs.AddressRecord,
        tx_name: str,
        verify: bool = True,
        destination_dir: itp.FileType = ".",
    ) -> structs.TxRawOutput:
        """Withdraw reward to payment address.

        Args:
            stake_addr_record: An `structs.AddressRecord` tuple for the stake address with reward.
            dst_addr_record: An `structs.AddressRecord` tuple for the destination payment address.
            tx_name: A name of the transaction.
            verify: A bool indicating whether to verify that the reward was transferred correctly.
            destination_dir: A path to directory for storing artifacts (optional).
        """
        dst_address = dst_addr_record.address
        src_init_balance = self._clusterlib_obj.g_query.get_address_balance(dst_address)

        tx_files_withdrawal = structs.TxFiles(
            signing_key_files=[dst_addr_record.skey_file, stake_addr_record.skey_file],
        )

        tx_raw_withdrawal_output = self._clusterlib_obj.g_transaction.send_tx(
            src_address=dst_address,
            tx_name=f"{tx_name}_reward_withdrawal",
            tx_files=tx_files_withdrawal,
            withdrawals=[structs.TxOut(address=stake_addr_record.address, amount=-1)],
            destination_dir=destination_dir,
        )

        if not verify:
            return tx_raw_withdrawal_output

        # check that reward is 0
        if (
            self._clusterlib_obj.g_query.get_stake_addr_info(
                stake_addr_record.address
            ).reward_account_balance
            != 0
        ):
            msg = "Not all rewards were transferred."
            raise exceptions.CLIError(msg)

        # check that rewards were transferred
        src_reward_balance = self._clusterlib_obj.g_query.get_address_balance(dst_address)
        if (
            src_reward_balance
            != src_init_balance
            - tx_raw_withdrawal_output.fee
            + tx_raw_withdrawal_output.withdrawals[0].amount  # type: ignore
        ):
            msg = f"Incorrect balance for destination address `{dst_address}`."
            raise exceptions.CLIError(msg)

        return tx_raw_withdrawal_output

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: clusterlib_obj={id(self._clusterlib_obj)}>"
