"""Group of methods for governance."""
import logging
from pathlib import Path
from typing import Optional

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
from cardano_clusterlib import types  # pylint: disable=unused-import
from cardano_clusterlib.types import FileType
from cardano_clusterlib.types import UnpackableSequence


LOGGER = logging.getLogger(__name__)


class GovernanceGroup:
    def __init__(self, clusterlib_obj: "types.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj

    def gen_update_proposal(
        self,
        cli_args: UnpackableSequence,
        epoch: int,
        tx_name: str,
        destination_dir: FileType = ".",
    ) -> Path:
        """Create an update proposal.

        Args:
            cli_args: A list (iterable) of CLI arguments.
            epoch: An epoch where the update proposal will take effect.
            tx_name: A name of the transaction.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the update proposal file.
        """
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{tx_name}_update.proposal"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        self._clusterlib_obj.cli(
            [
                "governance",
                "create-update-proposal",
                *cli_args,
                "--out-file",
                str(out_file),
                "--epoch",
                str(epoch),
                *helpers._prepend_flag(
                    "--genesis-verification-key-file",
                    self._clusterlib_obj.g_genesis.genesis_keys.genesis_vkeys,
                ),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def gen_mir_cert_to_treasury(
        self,
        transfer: int,
        tx_name: str,
        destination_dir: FileType = ".",
    ) -> Path:
        """Create an MIR certificate to transfer from the reserves pot to the treasury pot.

        Args:
            transfer: An amount of Lovelace to transfer.
            tx_name: A name of the transaction.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the MIR certificate file.
        """
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{tx_name}_mir_to_treasury.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        self._clusterlib_obj.cli(
            [
                "governance",
                "create-mir-certificate",
                "transfer-to-treasury",
                "--transfer",
                str(transfer),
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def gen_mir_cert_to_rewards(
        self,
        transfer: int,
        tx_name: str,
        destination_dir: FileType = ".",
    ) -> Path:
        """Create an MIR certificate to transfer from the treasury pot to the reserves pot.

        Args:
            transfer: An amount of Lovelace to transfer.
            tx_name: A name of the transaction.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the MIR certificate file.
        """
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{tx_name}_mir_to_rewards.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        self._clusterlib_obj.cli(
            [
                "governance",
                "create-mir-certificate",
                "transfer-to-rewards",
                "--transfer",
                str(transfer),
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def gen_mir_cert_stake_addr(
        self,
        stake_addr: str,
        reward: int,
        tx_name: str,
        use_treasury: bool = False,
        destination_dir: FileType = ".",
    ) -> Path:
        """Create an MIR certificate to pay stake addresses.

        Args:
            stake_addr: A stake address string.
            reward: An amount of Lovelace to transfer.
            tx_name: A name of the transaction.
            use_treasury: A bool indicating whether to use treasury or reserves (default).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the MIR certificate file.
        """
        destination_dir = Path(destination_dir).expanduser()
        funds_src = "treasury" if use_treasury else "reserves"
        out_file = destination_dir / f"{tx_name}_{funds_src}_mir_stake.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        self._clusterlib_obj.cli(
            [
                "governance",
                "create-mir-certificate",
                "stake-addresses",
                f"--{funds_src}",
                "--stake-address",
                str(stake_addr),
                "--reward",
                str(reward),
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def submit_update_proposal(
        self,
        cli_args: UnpackableSequence,
        src_address: str,
        src_skey_file: FileType,
        tx_name: str,
        epoch: Optional[int] = None,
        destination_dir: FileType = ".",
    ) -> structs.TxRawOutput:
        """Submit an update proposal.

        Args:
            cli_args: A list (iterable) of CLI arguments.
            src_address: An address used for fee and inputs.
            src_skey_file: A path to skey file corresponding to the `src_address`.
            tx_name: A name of the transaction.
            epoch: An epoch where the update proposal will take effect (optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            structs.TxRawOutput: A tuple with transaction output details.
        """
        # TODO: assumption is update proposals submitted near beginning of epoch
        epoch = epoch if epoch is not None else self._clusterlib_obj.g_query.get_epoch()

        out_file = self.gen_update_proposal(
            cli_args=cli_args,
            epoch=epoch,
            tx_name=tx_name,
            destination_dir=destination_dir,
        )

        return self._clusterlib_obj.g_transaction.send_tx(
            src_address=src_address,
            tx_name=f"{tx_name}_submit_proposal",
            tx_files=structs.TxFiles(
                proposal_files=[out_file],
                signing_key_files=[
                    *self._clusterlib_obj.g_genesis.genesis_keys.delegate_skeys,
                    Path(src_skey_file),
                ],
            ),
            destination_dir=destination_dir,
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: clusterlib_obj={id(self._clusterlib_obj)}>"
