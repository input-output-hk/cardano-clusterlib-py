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
            raise AssertionError("Either `stake_vkey_file` or `stake_script_file` is needed.")

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
        stake_vkey_file: tp.Optional[itp.FileType] = None,
        stake_script_file: tp.Optional[itp.FileType] = None,
        stake_address: tp.Optional[str] = None,
        era: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a stake address registration certificate.

        Args:
            addr_name: A name of stake address.
            stake_vkey_file: A path to corresponding stake vkey file (optional).
            stake_script_file: A path to corresponding stake script file (optional).
            stake_address: Stake address key, bech32 or hex-encoded (optional).
            era: An era for which to create the registration certificate (default: current era).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated certificate.
        """
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{addr_name}_stake_reg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        if stake_vkey_file:
            cli_args = ["--stake-verification-key-file", str(stake_vkey_file)]
        elif stake_script_file:
            cli_args = ["--stake-script-file", str(stake_script_file)]
        elif stake_address:
            cli_args = ["--stake-address", stake_address]
        else:
            raise AssertionError(
                "Either `stake_vkey_file`, `stake_script_file` or `stake_address` is needed."
            )

        era_arg = [f"--{era}-era"] if era else self._clusterlib_obj.get_cert_era_arg()

        self._clusterlib_obj.cli(
            [
                "stake-address",
                "registration-certificate",
                *era_arg,
                *cli_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def gen_stake_addr_deregistration_cert(
        self,
        addr_name: str,
        stake_vkey_file: tp.Optional[itp.FileType] = None,
        stake_script_file: tp.Optional[itp.FileType] = None,
        stake_address: tp.Optional[str] = None,
        era: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a stake address deregistration certificate.

        Args:
            addr_name: A name of stake address.
            stake_vkey_file: A path to corresponding stake vkey file (optional).
            stake_script_file: A path to corresponding stake script file (optional).
            stake_address: Stake address key, bech32 or hex-encoded (optional).
            era: An era in which the address was registered (default: current era).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated certificate.
        """
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{addr_name}_stake_dereg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        if stake_vkey_file:
            cli_args = ["--stake-verification-key-file", str(stake_vkey_file)]
        elif stake_script_file:
            cli_args = ["--stake-script-file", str(stake_script_file)]
        elif stake_address:
            cli_args = ["--stake-address", stake_address]
        else:
            raise AssertionError(
                "Either `stake_vkey_file`, `stake_script_file` or `stake_address` is needed."
            )

        era_arg = [f"--{era}-era"] if era else self._clusterlib_obj.get_cert_era_arg()

        self._clusterlib_obj.cli(
            [
                "stake-address",
                "deregistration-certificate",
                *era_arg,
                *cli_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def gen_stake_addr_delegation_cert(
        self,
        addr_name: str,
        stake_vkey_file: tp.Optional[itp.FileType] = None,
        stake_script_file: tp.Optional[itp.FileType] = None,
        stake_address: tp.Optional[str] = None,
        cold_vkey_file: tp.Optional[itp.FileType] = None,
        stake_pool_id: str = "",
        era: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a stake address delegation certificate.

        Args:
            addr_name: A name of stake address.
            stake_vkey_file: A path to corresponding stake vkey file (optional).
            stake_script_file: A path to corresponding stake script file (optional).
            stake_address: Stake address key, bech32 or hex-encoded (optional).
            cold_vkey_file: A path to pool cold vkey file (optional).
            stake_pool_id: An ID of the stake pool (optional).
            era: An era for which to create the delegation certificate (default: current era).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated certificate.
        """
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{addr_name}_stake_deleg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        cli_args = []
        if stake_vkey_file:
            cli_args.extend(["--stake-verification-key-file", str(stake_vkey_file)])
        elif stake_script_file:
            cli_args.extend(["--stake-script-file", str(stake_script_file)])
        elif stake_address:
            cli_args = ["--stake-address", stake_address]
        else:
            raise AssertionError(
                "Either `stake_vkey_file`, `stake_script_file` or `stake_address` is needed."
            )

        if cold_vkey_file:
            cli_args.extend(
                [
                    "--cold-verification-key-file",
                    str(cold_vkey_file),
                ]
            )
        elif stake_pool_id:
            cli_args.extend(
                [
                    "--stake-pool-id",
                    str(stake_pool_id),
                ]
            )
        else:
            raise AssertionError("Either `cold_vkey_file` or `stake_pool_id` is needed.")

        era_arg = [f"--{era}-era"] if era else self._clusterlib_obj.get_cert_era_arg()

        self._clusterlib_obj.cli(
            [
                "stake-address",
                "delegation-certificate",
                *era_arg,
                *cli_args,
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
            raise AssertionError("Either `stake_vkey` or `stake_vkey_file` is needed.")

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
            raise exceptions.CLIError("Not all rewards were transferred.")

        # check that rewards were transferred
        src_reward_balance = self._clusterlib_obj.g_query.get_address_balance(dst_address)
        if (
            src_reward_balance
            != src_init_balance
            - tx_raw_withdrawal_output.fee
            + tx_raw_withdrawal_output.withdrawals[0].amount  # type: ignore
        ):
            raise exceptions.CLIError(f"Incorrect balance for destination address `{dst_address}`.")

        return tx_raw_withdrawal_output

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: clusterlib_obj={id(self._clusterlib_obj)}>"
