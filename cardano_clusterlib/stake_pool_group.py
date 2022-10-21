"""Group of methods for working with stake pools."""
import logging
from pathlib import Path
from typing import List
from typing import Optional
from typing import Tuple

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
from cardano_clusterlib import types  # pylint: disable=unused-import
from cardano_clusterlib.types import FileType
from cardano_clusterlib.types import FileTypeList


LOGGER = logging.getLogger(__name__)


class StakePoolGroup:
    def __init__(self, clusterlib_obj: "types.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj

    def gen_pool_metadata_hash(self, pool_metadata_file: FileType) -> str:
        """Generate the hash of pool metadata.

        Args:
            pool_metadata_file: A path to the pool metadata file.

        Returns:
            str: A metadata hash.
        """
        return (
            self._clusterlib_obj.cli(
                ["stake-pool", "metadata-hash", "--pool-metadata-file", str(pool_metadata_file)]
            )
            .stdout.rstrip()
            .decode("ascii")
        )

    def gen_pool_registration_cert(
        self,
        pool_data: structs.PoolData,
        vrf_vkey_file: FileType,
        cold_vkey_file: FileType,
        owner_stake_vkey_files: FileTypeList,
        reward_account_vkey_file: Optional[FileType] = None,
        destination_dir: FileType = ".",
    ) -> Path:
        """Generate a stake pool registration certificate.

        Args:
            pool_data: A `structs.PoolData` tuple containing info about the stake pool.
            vrf_vkey_file: A path to node VRF vkey file.
            cold_vkey_file: A path to pool cold vkey file.
            owner_stake_vkey_files: A list of paths to pool owner stake vkey files.
            reward_account_vkey_file: A path to pool reward account vkey file (optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated certificate.
        """
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{pool_data.pool_name}_pool_reg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        metadata_cmd = []
        if pool_data.pool_metadata_url and pool_data.pool_metadata_hash:
            metadata_cmd = [
                "--metadata-url",
                str(pool_data.pool_metadata_url),
                "--metadata-hash",
                str(pool_data.pool_metadata_hash),
            ]

        relay_cmd = []
        if pool_data.pool_relay_dns:
            relay_cmd.extend(["--single-host-pool-relay", pool_data.pool_relay_dns])
        if pool_data.pool_relay_ipv4:
            relay_cmd.extend(["--pool-relay-ipv4", pool_data.pool_relay_ipv4])
        if pool_data.pool_relay_port:
            relay_cmd.extend(["--pool-relay-port", str(pool_data.pool_relay_port)])

        self._clusterlib_obj.cli(
            [
                "stake-pool",
                "registration-certificate",
                "--pool-pledge",
                str(pool_data.pool_pledge),
                "--pool-cost",
                str(pool_data.pool_cost),
                "--pool-margin",
                str(pool_data.pool_margin),
                "--vrf-verification-key-file",
                str(vrf_vkey_file),
                "--cold-verification-key-file",
                str(cold_vkey_file),
                "--pool-reward-account-verification-key-file",
                str(reward_account_vkey_file)
                if reward_account_vkey_file
                else str(list(owner_stake_vkey_files)[0]),
                *helpers._prepend_flag(
                    "--pool-owner-stake-verification-key-file", owner_stake_vkey_files
                ),
                *self._clusterlib_obj.magic_args,
                "--out-file",
                str(out_file),
                *metadata_cmd,
                *relay_cmd,
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def gen_pool_deregistration_cert(
        self, pool_name: str, cold_vkey_file: FileType, epoch: int, destination_dir: FileType = "."
    ) -> Path:
        """Generate a stake pool deregistration certificate.

        Args:
            pool_name: A name of the stake pool.
            cold_vkey_file: A path to pool cold vkey file.
            epoch: An epoch where the pool will be deregistered.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated certificate.
        """
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{pool_name}_pool_dereg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        self._clusterlib_obj.cli(
            [
                "stake-pool",
                "deregistration-certificate",
                "--cold-verification-key-file",
                str(cold_vkey_file),
                "--epoch",
                str(epoch),
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def get_stake_pool_id(self, cold_vkey_file: FileType) -> str:
        """Return pool ID from the offline key.

        Args:
            cold_vkey_file: A path to pool cold vkey file.

        Returns:
            str: A pool ID.
        """
        pool_id = (
            self._clusterlib_obj.cli(
                ["stake-pool", "id", "--cold-verification-key-file", str(cold_vkey_file)]
            )
            .stdout.strip()
            .decode("utf-8")
        )
        return pool_id

    def create_stake_pool(
        self,
        pool_data: structs.PoolData,
        pool_owners: List[structs.PoolUser],
        tx_name: str,
        destination_dir: FileType = ".",
    ) -> structs.PoolCreationOutput:
        """Create and register a stake pool.

        Args:
            pool_data: A `structs.PoolData` tuple containing info about the stake pool.
            pool_owners: A list of `structs.PoolUser` structures containing pool user addresses
                and keys.
            tx_name: A name of the transaction.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            structs.PoolCreationOutput: A tuple containing pool creation output.
        """
        # create the KES key pair
        node_kes = self._clusterlib_obj.g_node.gen_kes_key_pair(
            node_name=pool_data.pool_name,
            destination_dir=destination_dir,
        )
        LOGGER.debug(f"KES keys created - {node_kes.vkey_file}; {node_kes.skey_file}")

        # create the VRF key pair
        node_vrf = self._clusterlib_obj.g_node.gen_vrf_key_pair(
            node_name=pool_data.pool_name,
            destination_dir=destination_dir,
        )
        LOGGER.debug(f"VRF keys created - {node_vrf.vkey_file}; {node_vrf.skey_file}")

        # create the cold key pair and node operational certificate counter
        node_cold = self._clusterlib_obj.g_node.gen_cold_key_pair_and_counter(
            node_name=pool_data.pool_name,
            destination_dir=destination_dir,
        )
        LOGGER.debug(
            "Cold keys created and counter created - "
            f"{node_cold.vkey_file}; {node_cold.skey_file}; {node_cold.counter_file}"
        )

        pool_reg_cert_file, tx_raw_output = self.register_stake_pool(
            pool_data=pool_data,
            pool_owners=pool_owners,
            vrf_vkey_file=node_vrf.vkey_file,
            cold_key_pair=node_cold,
            tx_name=tx_name,
            destination_dir=destination_dir,
        )

        return structs.PoolCreationOutput(
            stake_pool_id=self.get_stake_pool_id(node_cold.vkey_file),
            vrf_key_pair=node_vrf,
            cold_key_pair=node_cold,
            pool_reg_cert_file=pool_reg_cert_file,
            pool_data=pool_data,
            pool_owners=pool_owners,
            tx_raw_output=tx_raw_output,
            kes_key_pair=node_kes,
        )

    def register_stake_pool(
        self,
        pool_data: structs.PoolData,
        pool_owners: List[structs.PoolUser],
        vrf_vkey_file: FileType,
        cold_key_pair: structs.ColdKeyPair,
        tx_name: str,
        reward_account_vkey_file: Optional[FileType] = None,
        deposit: Optional[int] = None,
        destination_dir: FileType = ".",
    ) -> Tuple[Path, structs.TxRawOutput]:
        """Register a stake pool.

        Args:
            pool_data: A `structs.PoolData` tuple containing info about the stake pool.
            pool_owners: A list of `structs.PoolUser` structures containing pool user addresses
                and keys.
            vrf_vkey_file: A path to node VRF vkey file.
            cold_key_pair: A `structs.ColdKeyPair` tuple containing the key pair and the counter.
            tx_name: A name of the transaction.
            reward_account_vkey_file: A path to reward account vkey file (optional).
            deposit: A deposit amount needed by the transaction (optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Tuple[Path, structs.TxRawOutput]: A tuple with pool registration cert file and
                transaction output details.
        """
        tx_name = f"{tx_name}_reg_pool"
        pool_reg_cert_file = self.gen_pool_registration_cert(
            pool_data=pool_data,
            vrf_vkey_file=vrf_vkey_file,
            cold_vkey_file=cold_key_pair.vkey_file,
            owner_stake_vkey_files=[p.stake.vkey_file for p in pool_owners],
            reward_account_vkey_file=reward_account_vkey_file,
            destination_dir=destination_dir,
        )

        # submit the pool registration certificate through a tx
        tx_files = structs.TxFiles(
            certificate_files=[pool_reg_cert_file],
            signing_key_files=[
                *[p.payment.skey_file for p in pool_owners],
                *[p.stake.skey_file for p in pool_owners],
                cold_key_pair.skey_file,
            ],
        )

        tx_raw_output = self._clusterlib_obj.g_transaction.send_tx(
            src_address=pool_owners[0].payment.address,
            tx_name=tx_name,
            tx_files=tx_files,
            deposit=deposit,
            destination_dir=destination_dir,
        )

        return pool_reg_cert_file, tx_raw_output

    def deregister_stake_pool(
        self,
        pool_owners: List[structs.PoolUser],
        cold_key_pair: structs.ColdKeyPair,
        epoch: int,
        pool_name: str,
        tx_name: str,
        destination_dir: FileType = ".",
    ) -> Tuple[Path, structs.TxRawOutput]:
        """Deregister a stake pool.

        Args:
            pool_owners: A list of `structs.PoolUser` structures containing pool user addresses
                and keys.
            cold_key_pair: A `structs.ColdKeyPair` tuple containing the key pair and the counter.
            epoch: An epoch where the update proposal will take effect (optional).
            pool_name: A name of the stake pool.
            tx_name: A name of the transaction.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Tuple[Path, structs.TxRawOutput]: A tuple with pool registration cert file and
                transaction output details.
        """
        tx_name = f"{tx_name}_dereg_pool"
        LOGGER.debug(
            f"Deregistering stake pool starting with epoch: {epoch}; "
            f"Current epoch is: {self._clusterlib_obj.g_query.get_epoch()}"
        )
        pool_dereg_cert_file = self.gen_pool_deregistration_cert(
            pool_name=pool_name,
            cold_vkey_file=cold_key_pair.vkey_file,
            epoch=epoch,
            destination_dir=destination_dir,
        )

        # submit the pool deregistration certificate through a tx
        tx_files = structs.TxFiles(
            certificate_files=[pool_dereg_cert_file],
            signing_key_files=[
                *[p.payment.skey_file for p in pool_owners],
                *[p.stake.skey_file for p in pool_owners],
                cold_key_pair.skey_file,
            ],
        )

        tx_raw_output = self._clusterlib_obj.g_transaction.send_tx(
            src_address=pool_owners[0].payment.address,
            tx_name=tx_name,
            tx_files=tx_files,
            destination_dir=destination_dir,
        )

        return pool_dereg_cert_file, tx_raw_output

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: clusterlib_obj={id(self._clusterlib_obj)}>"
