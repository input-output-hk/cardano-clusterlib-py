"""Group of methods for working with key commands."""

import logging
import pathlib as pl
import typing as tp

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import consts
from cardano_clusterlib import helpers
from cardano_clusterlib import types as itp

LOGGER = logging.getLogger(__name__)


class KeyGroup:
    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj

    def gen_verification_key(
        self,
        key_name: str,
        signing_key_file: itp.FileType,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a verification file from a signing key.

        Args:
            key_name: A name of the key.
            signing_key_file: A path to signing key file.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated verification key file.
        """
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{key_name}.vkey"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        self._clusterlib_obj.cli(
            [
                "key",
                "verification-key",
                "--signing-key-file",
                str(signing_key_file),
                "--verification-key-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def gen_non_extended_verification_key(
        self,
        key_name: str,
        extended_verification_key_file: itp.FileType,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Generate a non-extended key from a verification key.

        Args:
            key_name: A name of the key.
            extended_verification_key_file: A path to the extended verification key file.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated non-extended verification key file.
        """
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{key_name}.vkey"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        self._clusterlib_obj.cli(
            [
                "key",
                "non-extended-key",
                "--extended-verification-key-file",
                str(extended_verification_key_file),
                "--verification-key-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def gen_mnemonic(
        self,
        size: tp.Literal[12, 15, 18, 21, 24],
        out_file: itp.FileType = "",
    ) -> list[str]:
        """Generate a mnemonic sentence that can be used for key derivation.

        Args:
            size: Number of words in the mnemonic (12, 15, 18, 21, or 24).
            out_file: A path to a file where the mnemonic will be stored (optional).

        Returns:
            list[str]: A list of words in the generated mnemonic.
        """
        out_args = []
        if out_file:
            clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)
            out_args = ["--out-file", str(out_file)]

        out = (
            self._clusterlib_obj.cli(
                [
                    "key",
                    "generate-mnemonic",
                    *out_args,
                    "--size",
                    str(size),
                ]
            )
            .stdout.strip()
            .decode("ascii")
        )

        if out_file:
            helpers._check_outfiles(out_file)
            words = helpers.read_from_file(file=out_file).strip().split()
        else:
            words = out.split()

        return words

    def derive_from_mnemonic(
        self,
        key_name: str,
        key_type: consts.KeyType,
        mnemonic_file: itp.FileType,
        account_number: int = 0,
        key_number: int | None = None,
        out_format: consts.OutputFormat = consts.OutputFormat.TEXT_ENVELOPE,
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Derive an extended signing key from a mnemonic sentence.

        Args:
            key_name: A name of the key.
            key_type: A type of the key.
            mnemonic_file: A path to a file containing the mnemonic sentence.
            account_number: An account number (default is 0).
            key_number: A key number (optional, required for payment and stake keys).
            out_format: An output format (default is text-envelope).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated extended signing key file.
        """
        destination_dir = pl.Path(destination_dir).expanduser()
        out_file = destination_dir / f"{key_name}.skey"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        key_args = []
        key_number_err = f"`key_number` must be specified when key_type is '{key_type.value}'"
        if key_type == consts.KeyType.DREP:
            key_args.append("--drep-key")
        elif key_type == consts.KeyType.CC_COLD:
            key_args.append("--cc-cold-key")
        elif key_type == consts.KeyType.CC_HOT:
            key_args.append("--cc-hot-key")
        elif key_type == consts.KeyType.PAYMENT:
            if key_number is None:
                raise ValueError(key_number_err)
            key_args.extend(["--payment-key-with-number", str(key_number)])
        elif key_type == consts.KeyType.STAKE:
            if key_number is None:
                raise ValueError(key_number_err)
            key_args.extend(["--stake-key-with-number", str(key_number)])
        else:
            err = f"Unsupported key_type: {key_type}"
            raise ValueError(err)

        self._clusterlib_obj.cli(
            [
                "key",
                "derive-from-mnemonic",
                f"--key-output-{out_format.value}",
                *key_args,
                "--account-number",
                str(account_number),
                "--mnemonic-from-file",
                str(mnemonic_file),
                "--signing-key-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: clusterlib_obj={id(self._clusterlib_obj)}>"
