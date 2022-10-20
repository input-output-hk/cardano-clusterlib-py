"""Group of methods for node operation."""
import logging
from pathlib import Path
from typing import Optional

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
from cardano_clusterlib import types  # pylint: disable=unused-import
from cardano_clusterlib.types import FileType


LOGGER = logging.getLogger(__name__)


class NodeGroup:
    def __init__(self, clusterlib_obj: "types.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj

    def gen_kes_key_pair(self, node_name: str, destination_dir: FileType = ".") -> structs.KeyPair:
        """Generate a key pair for a node KES operational key.

        Args:
            node_name: A name of the node the key pair is generated for.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            structs.KeyPair: A tuple containing the key pair.
        """
        destination_dir = Path(destination_dir).expanduser()
        vkey = destination_dir / f"{node_name}_kes.vkey"
        skey = destination_dir / f"{node_name}_kes.skey"
        clusterlib_helpers._check_files_exist(vkey, skey, clusterlib_obj=self._clusterlib_obj)

        self._clusterlib_obj.cli(
            [
                "node",
                "key-gen-KES",
                "--verification-key-file",
                str(vkey),
                "--signing-key-file",
                str(skey),
            ]
        )

        helpers._check_outfiles(vkey, skey)
        return structs.KeyPair(vkey, skey)

    def gen_vrf_key_pair(self, node_name: str, destination_dir: FileType = ".") -> structs.KeyPair:
        """Generate a key pair for a node VRF operational key.

        Args:
            node_name: A name of the node the key pair is generated for.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            structs.KeyPair: A tuple containing the key pair.
        """
        destination_dir = Path(destination_dir).expanduser()
        vkey = destination_dir / f"{node_name}_vrf.vkey"
        skey = destination_dir / f"{node_name}_vrf.skey"
        clusterlib_helpers._check_files_exist(vkey, skey, clusterlib_obj=self._clusterlib_obj)

        self._clusterlib_obj.cli(
            [
                "node",
                "key-gen-VRF",
                "--verification-key-file",
                str(vkey),
                "--signing-key-file",
                str(skey),
            ]
        )

        helpers._check_outfiles(vkey, skey)
        return structs.KeyPair(vkey, skey)

    def gen_cold_key_pair_and_counter(
        self, node_name: str, destination_dir: FileType = "."
    ) -> structs.ColdKeyPair:
        """Generate a key pair for operator's offline key and a new certificate issue counter.

        Args:
            node_name: A name of the node the key pair and the counter is generated for.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            structs.ColdKeyPair: A tuple containing the key pair and the counter.
        """
        destination_dir = Path(destination_dir).expanduser()
        vkey = destination_dir / f"{node_name}_cold.vkey"
        skey = destination_dir / f"{node_name}_cold.skey"
        counter = destination_dir / f"{node_name}_cold.counter"
        clusterlib_helpers._check_files_exist(
            vkey, skey, counter, clusterlib_obj=self._clusterlib_obj
        )

        self._clusterlib_obj.cli(
            [
                "node",
                "key-gen",
                "--cold-verification-key-file",
                str(vkey),
                "--cold-signing-key-file",
                str(skey),
                "--operational-certificate-issue-counter-file",
                str(counter),
            ]
        )

        helpers._check_outfiles(vkey, skey, counter)
        return structs.ColdKeyPair(vkey, skey, counter)

    def gen_node_operational_cert(
        self,
        node_name: str,
        kes_vkey_file: FileType,
        cold_skey_file: FileType,
        cold_counter_file: FileType,
        kes_period: Optional[int] = None,
        destination_dir: FileType = ".",
    ) -> Path:
        """Generate a node operational certificate.

        This certificate is used when starting the node and not submitted through a transaction.

        Args:
            node_name: A name of the node the certificate is generated for.
            kes_vkey_file: A path to pool KES vkey file.
            cold_skey_file: A path to pool cold skey file.
            cold_counter_file: A path to pool cold counter file.
            kes_period: A start KES period. The current KES period is used when not specified.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated certificate.
        """
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{node_name}.opcert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        kes_period = (
            kes_period if kes_period is not None else self._clusterlib_obj.g_query.get_kes_period()
        )

        self._clusterlib_obj.cli(
            [
                "node",
                "issue-op-cert",
                "--kes-verification-key-file",
                str(kes_vkey_file),
                "--cold-signing-key-file",
                str(cold_skey_file),
                "--operational-certificate-issue-counter",
                str(cold_counter_file),
                "--kes-period",
                str(kes_period),
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: clusterlib_obj={id(self._clusterlib_obj)}>"
