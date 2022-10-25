"""Group of methods for working with key commands."""
import logging
from pathlib import Path

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import helpers
from cardano_clusterlib import types  # pylint: disable=unused-import
from cardano_clusterlib.types import FileType


LOGGER = logging.getLogger(__name__)


class KeyGroup:
    def __init__(self, clusterlib_obj: "types.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj

    def gen_verification_key(
        self, key_name: str, signing_key_file: FileType, destination_dir: FileType = "."
    ) -> Path:
        """Generate a verification file from a signing key.

        Args:
            key_name: A name of the key.
            signing_key_file: A path to signing key file.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated verification key file.
        """
        destination_dir = Path(destination_dir).expanduser()
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
        extended_verification_key_file: FileType,
        destination_dir: FileType = ".",
    ) -> Path:
        """Generate a non-extended key from a verification key.

        Args:
            key_name: A name of the key.
            extended_verification_key_file: A path to the extended verification key file.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated non-extended verification key file.
        """
        destination_dir = Path(destination_dir).expanduser()
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

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: clusterlib_obj={id(self._clusterlib_obj)}>"
