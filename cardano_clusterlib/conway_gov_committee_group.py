"""Group of methods for Conway governance committee commands."""

import logging
import pathlib as pl
import typing as tp

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
from cardano_clusterlib import types as itp

LOGGER = logging.getLogger(__name__)


class ConwayGovCommitteeGroup:
    def __init__(self, clusterlib_obj: "itp.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj
        self._group_args = ("governance", "committee")

    def _get_cold_vkey_args(
        self,
        cold_vkey: str = "",
        cold_vkey_file: itp.FileType = "",
        cold_vkey_hash: str = "",
    ) -> tp.List[str]:
        """Get arguments for cold verification key."""
        if cold_vkey:
            key_args = ["--cold-verification-key", str(cold_vkey)]
        elif cold_vkey_file:
            key_args = ["--cold-verification-key-file", str(cold_vkey_file)]
        elif cold_vkey_hash:
            key_args = ["--cold-key-hash", str(cold_vkey_hash)]
        else:
            msg = "Either `cold_vkey`, `cold_vkey_file` or `cold_vkey_hash` is needed."
            raise AssertionError(msg)

        return key_args

    def gen_cold_key_resignation_cert(
        self,
        key_name: str,
        cold_vkey: str = "",
        cold_vkey_file: itp.FileType = "",
        cold_vkey_hash: str = "",
        resignation_metadata_url: str = "",
        resignation_metadata_hash: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Create cold key resignation certificate for a Constitutional Committee Member."""
        destination_dir = pl.Path(destination_dir).expanduser()
        cert_file = destination_dir / f"{key_name}_committee_cold_resignation.cert"
        clusterlib_helpers._check_files_exist(cert_file, clusterlib_obj=self._clusterlib_obj)

        key_args = self._get_cold_vkey_args(
            cold_vkey=cold_vkey, cold_vkey_file=cold_vkey_file, cold_vkey_hash=cold_vkey_hash
        )

        self._clusterlib_obj.cli(
            [
                *self._group_args,
                "create-cold-key-resignation-certificate",
                *key_args,
                "--resignation-metadata-url",
                resignation_metadata_url,
                "--resignation-metadata-hash",
                resignation_metadata_hash,
                "--out-file",
                str(cert_file),
            ]
        )

        helpers._check_outfiles(cert_file)
        return cert_file

    def gen_hot_key_auth_cert(
        self,
        key_name: str,
        cold_vkey: str = "",
        cold_vkey_file: itp.FileType = "",
        cold_vkey_hash: str = "",
        hot_key: str = "",
        hot_key_file: itp.FileType = "",
        hot_key_hash: str = "",
        destination_dir: itp.FileType = ".",
    ) -> pl.Path:
        """Create hot key authorization certificate for a Constitutional Committee Member."""
        destination_dir = pl.Path(destination_dir).expanduser()
        cert_file = destination_dir / f"{key_name}_committee_hot_auth.cert"
        clusterlib_helpers._check_files_exist(cert_file, clusterlib_obj=self._clusterlib_obj)

        cold_vkey_args = self._get_cold_vkey_args(
            cold_vkey=cold_vkey, cold_vkey_file=cold_vkey_file, cold_vkey_hash=cold_vkey_hash
        )

        if hot_key:
            hot_key_args = ["--hot-key", str(hot_key)]
        elif hot_key_file:
            hot_key_args = ["--hot-key-file", str(hot_key_file)]
        elif hot_key_hash:
            hot_key_args = ["--hot-key-hash", str(hot_key_hash)]
        else:
            msg = "Either `hot_key`, `hot_key_file` or `hot_key_hash` is needed."
            raise AssertionError(msg)

        self._clusterlib_obj.cli(
            [
                *self._group_args,
                "create-hot-key-authorization-certificate",
                *cold_vkey_args,
                *hot_key_args,
                "--out-file",
                str(cert_file),
            ]
        )

        helpers._check_outfiles(cert_file)
        return cert_file

    def gen_cold_key_pair(
        self, key_name: str, destination_dir: itp.FileType = "."
    ) -> structs.KeyPair:
        """Create a cold key pair for a Constitutional Committee Member."""
        destination_dir = pl.Path(destination_dir).expanduser()
        vkey = destination_dir / f"{key_name}_committee_cold.vkey"
        skey = destination_dir / f"{key_name}_committee_cold.skey"
        clusterlib_helpers._check_files_exist(vkey, skey, clusterlib_obj=self._clusterlib_obj)

        self._clusterlib_obj.cli(
            [
                *self._group_args,
                "key-gen-cold",
                "--cold-verification-key-file",
                str(vkey),
                "--cold-signing-key-file",
                str(skey),
            ]
        )

        helpers._check_outfiles(vkey, skey)
        return structs.KeyPair(vkey, skey)

    def gen_hot_key_pair(
        self, key_name: str, destination_dir: itp.FileType = "."
    ) -> structs.KeyPair:
        """Create a cold key pair for a Constitutional Committee Member."""
        destination_dir = pl.Path(destination_dir).expanduser()
        vkey = destination_dir / f"{key_name}_committee_hot.vkey"
        skey = destination_dir / f"{key_name}_committee_hot.skey"
        clusterlib_helpers._check_files_exist(vkey, skey, clusterlib_obj=self._clusterlib_obj)

        self._clusterlib_obj.cli(
            [
                *self._group_args,
                "key-gen-hot",
                "--verification-key-file",
                str(vkey),
                "--signing-key-file",
                str(skey),
            ]
        )

        helpers._check_outfiles(vkey, skey)
        return structs.KeyPair(vkey, skey)

    def get_key_hash(
        self,
        vkey: str = "",
        vkey_file: itp.FileType = "",
    ) -> str:
        """Get the identifier (hash) of a public key."""
        vkey_file = pl.Path(vkey_file).expanduser()
        clusterlib_helpers._check_files_exist(vkey_file, clusterlib_obj=self._clusterlib_obj)

        if vkey:
            key_args = ["--verification-key", str(vkey)]
        elif vkey_file:
            key_args = ["--verification-key-file", str(vkey_file)]
        else:
            msg = "Either `vkey` or `vkey_file` is needed."
            raise AssertionError(msg)

        key_hash = (
            self._clusterlib_obj.cli([*self._group_args, "key-hash", *key_args])
            .stdout.rstrip()
            .decode("ascii")
        )

        return key_hash
