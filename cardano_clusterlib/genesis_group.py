"""Group of methods related to genesis block."""
import logging
from pathlib import Path
from typing import Optional

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import exceptions
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
from cardano_clusterlib import types  # pylint: disable=unused-import
from cardano_clusterlib.types import FileType


LOGGER = logging.getLogger(__name__)


class GenesisGroup:
    def __init__(self, clusterlib_obj: "types.ClusterLib") -> None:
        self._clusterlib_obj = clusterlib_obj

        self._genesis_keys: Optional[structs.GenesisKeys] = None
        self._genesis_utxo_addr: str = ""

    @property
    def genesis_keys(self) -> structs.GenesisKeys:
        """Return tuple with genesis-related keys."""
        if self._genesis_keys:
            return self._genesis_keys

        genesis_utxo_vkey = self._clusterlib_obj.state_dir / "shelley" / "genesis-utxo.vkey"
        genesis_utxo_skey = self._clusterlib_obj.state_dir / "shelley" / "genesis-utxo.skey"
        genesis_vkeys = list(
            self._clusterlib_obj.state_dir.glob("shelley/genesis-keys/genesis?.vkey")
        )
        delegate_skeys = list(
            self._clusterlib_obj.state_dir.glob("shelley/delegate-keys/delegate?.skey")
        )

        if not genesis_vkeys:
            raise exceptions.CLIError("The genesis verification keys don't exist.")
        if not delegate_skeys:
            raise exceptions.CLIError("The delegation signing keys don't exist.")

        for file_name in (
            genesis_utxo_vkey,
            genesis_utxo_skey,
        ):
            if not file_name.exists():
                raise exceptions.CLIError(f"The file `{file_name}` doesn't exist.")

        genesis_keys = structs.GenesisKeys(
            genesis_utxo_vkey=genesis_utxo_skey,
            genesis_utxo_skey=genesis_utxo_skey,
            genesis_vkeys=genesis_vkeys,
            delegate_skeys=delegate_skeys,
        )

        self._genesis_keys = genesis_keys

        return genesis_keys

    @property
    def genesis_utxo_addr(self) -> str:
        """Produce a genesis UTxO address."""
        if self._genesis_utxo_addr:
            return self._genesis_utxo_addr

        self._genesis_utxo_addr = self.gen_genesis_addr(
            addr_name=f"genesis-{self._clusterlib_obj._rand_str}",
            vkey_file=self.genesis_keys.genesis_utxo_vkey,
            destination_dir=self._clusterlib_obj.state_dir,
        )

        return self._genesis_utxo_addr

    def gen_genesis_addr(
        self, addr_name: str, vkey_file: FileType, destination_dir: FileType = "."
    ) -> str:
        """Generate the address for an initial UTxO based on the verification key.

        Args:
            addr_name: A name of genesis address.
            vkey_file: A path to corresponding vkey file.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            str: A generated genesis address.
        """
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{addr_name}_genesis.addr"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self._clusterlib_obj)

        self._clusterlib_obj.cli(
            [
                "genesis",
                "initial-addr",
                *self._clusterlib_obj.magic_args,
                "--verification-key-file",
                str(vkey_file),
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return helpers.read_address_from_file(out_file)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: clusterlib_obj={id(self._clusterlib_obj)}>"
