"""Group of methods for working with payment addresses."""
import json
import logging
import warnings
from pathlib import Path
from typing import Dict
from typing import Optional

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
from cardano_clusterlib import types  # pylint: disable=unused-import
from cardano_clusterlib.types import FileType


LOGGER = logging.getLogger(__name__)


class AddressGroup:
    def __init__(self, clusterlib_obj: "types.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj

    def gen_payment_addr(
        self,
        addr_name: str,
        payment_vkey_file: Optional[FileType] = None,
        payment_script_file: Optional[FileType] = None,
        stake_vkey_file: Optional[FileType] = None,
        stake_script_file: Optional[FileType] = None,
        destination_dir: FileType = ".",
    ) -> str:
        """Generate a payment address, with optional delegation to a stake address.

        Args:
            addr_name: A name of payment address.
            payment_vkey_file: A path to corresponding vkey file (optional).
            payment_script_file: A path to corresponding payment script file (optional).
            stake_vkey_file: A path to corresponding stake vkey file (optional).
            stake_script_file: A path to corresponding payment script file (optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            str: A generated payment address.
        """
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{addr_name}.addr"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        if payment_vkey_file:
            cli_args = ["--payment-verification-key-file", str(payment_vkey_file)]
        elif payment_script_file:
            cli_args = ["--payment-script-file", str(payment_script_file)]
        else:
            raise AssertionError("Either `payment_vkey_file` or `payment_script_file` is needed.")

        if stake_vkey_file:
            cli_args.extend(["--stake-verification-key-file", str(stake_vkey_file)])
        elif stake_script_file:
            cli_args.extend(["--stake-script-file", str(stake_script_file)])

        self._clusterlib_obj.cli(
            [
                "address",
                "build",
                *self._clusterlib_obj.magic_args,
                *cli_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return helpers.read_address_from_file(out_file)

    def gen_payment_key_pair(
        self, key_name: str, extended: bool = False, destination_dir: FileType = "."
    ) -> structs.KeyPair:
        """Generate an address key pair.

        Args:
            key_name: A name of the key pair.
            extended: A bool indicating whether to generate extended ed25519 Shelley-era key
                (False by default).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            structs.KeyPair: A tuple containing the key pair.
        """
        destination_dir = Path(destination_dir).expanduser()
        vkey = destination_dir / f"{key_name}.vkey"
        skey = destination_dir / f"{key_name}.skey"
        clusterlib_helpers._check_files_exist(vkey, skey, clusterlib_obj=self._clusterlib_obj)

        extended_args = ["--extended-key"] if extended else []

        self._clusterlib_obj.cli(
            [
                "address",
                "key-gen",
                "--verification-key-file",
                str(vkey),
                *extended_args,
                "--signing-key-file",
                str(skey),
            ]
        )

        helpers._check_outfiles(vkey, skey)
        return structs.KeyPair(vkey, skey)

    def get_payment_vkey_hash(
        self,
        payment_vkey_file: FileType,
    ) -> str:
        """Return the hash of an address key.

        Args:
            payment_vkey_file: A path to payment vkey file.

        Returns:
            str: A generated hash.
        """
        return (
            self._clusterlib_obj.cli(
                ["address", "key-hash", "--payment-verification-key-file", str(payment_vkey_file)]
            )
            .stdout.rstrip()
            .decode("ascii")
        )

    def get_address_info(
        self,
        address: str,
    ) -> structs.AddressInfo:
        """Get information about an address.

        Args:
            address: A Cardano address.

        Returns:
            structs.AddressInfo: A tuple containing address info.
        """
        addr_dict: Dict[str, str] = json.loads(
            self._clusterlib_obj.cli(["address", "info", "--address", str(address)])
            .stdout.rstrip()
            .decode("utf-8")
        )
        return structs.AddressInfo(**addr_dict)

    def gen_script_addr(
        self, addr_name: str, script_file: FileType, destination_dir: FileType = "."
    ) -> str:
        """Generate a script address.

        Args:
            addr_name: A name of payment address.
            script_file: A path to corresponding script file.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            str: A generated script address.
        """
        warnings.warn("`gen_script_addr` deprecated by `gen_payment_addr`", DeprecationWarning)
        return self.gen_payment_addr(
            addr_name=addr_name, payment_script_file=script_file, destination_dir=destination_dir
        )

    def gen_payment_addr_and_keys(
        self,
        name: str,
        stake_vkey_file: Optional[FileType] = None,
        stake_script_file: Optional[FileType] = None,
        destination_dir: FileType = ".",
    ) -> structs.AddressRecord:
        """Generate payment address and key pair.

        Args:
            name: A name of the address and key pair.
            stake_vkey_file: A path to corresponding stake vkey file (optional).
            stake_script_file: A path to corresponding payment script file (optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            structs.AddressRecord: A tuple containing the address and key pair / script file.
        """
        key_pair = self.gen_payment_key_pair(key_name=name, destination_dir=destination_dir)
        addr = self.gen_payment_addr(
            addr_name=name,
            payment_vkey_file=key_pair.vkey_file,
            stake_vkey_file=stake_vkey_file,
            stake_script_file=stake_script_file,
            destination_dir=destination_dir,
        )

        return structs.AddressRecord(
            address=addr, vkey_file=key_pair.vkey_file, skey_file=key_pair.skey_file
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: clusterlib_obj={id(self._clusterlib_obj)}>"
