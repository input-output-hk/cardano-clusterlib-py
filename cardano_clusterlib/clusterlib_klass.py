"""Wrapper for cardano-cli for working with cardano cluster."""
import datetime
import functools
import itertools
import json
import logging
import subprocess
import time
import warnings
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import consts
from cardano_clusterlib import coverage
from cardano_clusterlib import exceptions
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
from cardano_clusterlib import txtools
from cardano_clusterlib.types import FileType
from cardano_clusterlib.types import FileTypeList
from cardano_clusterlib.types import OptionalFiles
from cardano_clusterlib.types import UnpackableSequence


LOGGER = logging.getLogger(__name__)


class ClusterLib:
    """Methods for working with cardano cluster using `cardano-cli`..

    Attributes:
        state_dir: A directory with cluster state files (keys, config files, logs, ...).
        protocol: A cluster protocol - full cardano mode by default.
        tx_era: An era used for transactions, by default same as network Era.
        slots_offset: Difference in slots between cluster's start era and current era
            (e.g. Byron->Mary)
    """

    # pylint: disable=too-many-public-methods,too-many-instance-attributes

    def __init__(
        self,
        state_dir: FileType,
        protocol: str = consts.Protocols.CARDANO,
        tx_era: str = "",
        slots_offset: int = 0,
    ):
        self.cluster_id = 0  # can be used for identifying cluster instance
        self.cli_coverage: dict = {}
        self._rand_str = helpers.get_rand_str(4)
        self._cli_log = ""

        self.state_dir = Path(state_dir).expanduser().resolve()
        if not self.state_dir.exists():
            raise exceptions.CLIError(f"The state dir `{self.state_dir}` doesn't exist.")

        self.pparams_file = self.state_dir / f"pparams-{self._rand_str}.json"

        self.genesis_json = clusterlib_helpers._find_genesis_json(clusterlib_obj=self)
        with open(self.genesis_json, encoding="utf-8") as in_json:
            self.genesis = json.load(in_json)

        self.slot_length = self.genesis["slotLength"]
        self.epoch_length = self.genesis["epochLength"]
        self.epoch_length_sec = self.epoch_length * self.slot_length
        self.slots_per_kes_period = self.genesis["slotsPerKESPeriod"]
        self.max_kes_evolutions = self.genesis["maxKESEvolutions"]

        self.network_magic = self.genesis["networkMagic"]
        if self.network_magic == consts.MAINNET_MAGIC:
            self.magic_args = ["--mainnet"]
        else:
            self.magic_args = ["--testnet-magic", str(self.network_magic)]

        self.slots_offset = slots_offset or consts.SLOTS_OFFSETS.get(self.network_magic) or 0
        self.ttl_length = 1000
        # TODO: proper calculation based on `utxoCostPerWord` needed
        self._min_change_value = 1800_000

        self.tx_era = tx_era
        self.tx_era_arg = [f"--{self.tx_era.lower()}-era"] if self.tx_era else []

        # TODO: add temporary switch for CDDL format, until it is made default
        self.use_cddl = False

        self.protocol = protocol
        clusterlib_helpers._check_protocol(clusterlib_obj=self)

        self._genesis_keys: Optional[structs.GenesisKeys] = None
        self._genesis_utxo_addr: str = ""

        self.overwrite_outfiles = True

    @property
    def genesis_keys(self) -> structs.GenesisKeys:
        """Return tuple with genesis-related keys."""
        if self._genesis_keys:
            return self._genesis_keys

        genesis_utxo_vkey = self.state_dir / "shelley" / "genesis-utxo.vkey"
        genesis_utxo_skey = self.state_dir / "shelley" / "genesis-utxo.skey"
        genesis_vkeys = list(self.state_dir.glob("shelley/genesis-keys/genesis?.vkey"))
        delegate_skeys = list(self.state_dir.glob("shelley/delegate-keys/delegate?.skey"))

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
            addr_name=f"genesis-{self._rand_str}",
            vkey_file=self.genesis_keys.genesis_utxo_vkey,
            destination_dir=self.state_dir,
        )

        return self._genesis_utxo_addr

    def cli_base(self, cli_args: List[str]) -> structs.CLIOut:
        """Run a command.

        Args:
            cli_args: A list consisting of command and it's arguments.

        Returns:
            structs.CLIOut: A tuple containing command stdout and stderr.
        """
        cmd_str = " ".join(cli_args)
        LOGGER.debug("Running `%s`", cmd_str)
        clusterlib_helpers._write_cli_log(clusterlib_obj=self, command=cmd_str)

        # re-run the command when running into
        # Network.Socket.connect: <socket: X>: resource exhausted (Resource temporarily unavailable)
        # or
        # MuxError (MuxIOException writev: resource vanished (Broken pipe)) "(sendAll errored)"
        for __ in range(3):
            with subprocess.Popen(cli_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
                stdout, stderr = p.communicate()

                if p.returncode == 0:
                    break

            stderr_dec = stderr.decode()
            err_msg = (
                f"An error occurred running a CLI command `{cmd_str}` on path "
                f"`{Path.cwd()}`: {stderr_dec}"
            )
            if "resource exhausted" in stderr_dec or "resource vanished" in stderr_dec:
                LOGGER.error(err_msg)
                time.sleep(0.4)
                continue
            raise exceptions.CLIError(err_msg)
        else:
            raise exceptions.CLIError(err_msg)

        return structs.CLIOut(stdout or b"", stderr or b"")

    def cli(self, cli_args: List[str]) -> structs.CLIOut:
        """Run the `cardano-cli` command.

        Args:
            cli_args: A list of arguments for cardano-cli.

        Returns:
            structs.CLIOut: A tuple containing command stdout and stderr.
        """
        cmd = ["cardano-cli", *cli_args]
        coverage.record_cli_coverage(cli_args=cmd, coverage_dict=self.cli_coverage)
        return self.cli_base(cmd)

    def query_cli(self, cli_args: UnpackableSequence) -> str:
        """Run the `cardano-cli query` command."""
        stdout = self.cli(
            [
                "query",
                *cli_args,
                *self.magic_args,
                f"--{self.protocol}-mode",
            ]
        ).stdout
        stdout_dec = stdout.decode("utf-8") if stdout else ""
        return stdout_dec

    def refresh_pparams_file(self) -> None:
        """Refresh protocol parameters file."""
        self.query_cli(["protocol-parameters", "--out-file", str(self.pparams_file)])

    def create_pparams_file(self) -> None:
        """Create protocol parameters file if it doesn't exist."""
        if self.pparams_file.exists():
            return
        self.refresh_pparams_file()

    def get_utxo(
        self,
        address: Union[str, List[str]] = "",
        txin: Union[str, List[str]] = "",
        utxo: Union[structs.UTXOData, structs.OptionalUTXOData] = (),
        tx_raw_output: Optional[structs.TxRawOutput] = None,
        coins: UnpackableSequence = (),
    ) -> List[structs.UTXOData]:
        """Return UTxO info for payment address.

        Args:
            address: Payment address(es).
            txin: Transaction input(s) (TxId#TxIx).
            utxo: Representation of UTxO data (`structs.UTXOData`).
            tx_raw_output: A data used when building a transaction (`structs.TxRawOutput`).
            coins: A list (iterable) of coin names (asset IDs, optional).

        Returns:
            List[structs.UTXOData]: A list of UTxO data.
        """
        cli_args = ["utxo", "--out-file", "/dev/stdout"]

        address_single = ""
        if address:
            if isinstance(address, str):
                address_single = address
                address = [address]
            cli_args.extend(helpers._prepend_flag("--address", address))
        elif txin:
            if isinstance(txin, str):
                txin = [txin]
            cli_args.extend(helpers._prepend_flag("--tx-in", txin))
        elif utxo:
            if isinstance(utxo, structs.UTXOData):
                utxo = [utxo]
            utxo_formatted = [f"{u.utxo_hash}#{u.utxo_ix}" for u in utxo]
            cli_args.extend(helpers._prepend_flag("--tx-in", utxo_formatted))
        elif tx_raw_output:  # noqa: SIM106
            change_txout_num = 1 if tx_raw_output.change_address else 0
            num_of_txouts = len(tx_raw_output.txouts) + change_txout_num
            utxo_hash = self.get_txid(tx_body_file=tx_raw_output.out_file)
            utxo_formatted = [f"{utxo_hash}#{ix}" for ix in range(num_of_txouts)]
            cli_args.extend(helpers._prepend_flag("--tx-in", utxo_formatted))
        else:
            raise AssertionError(
                "Either `address`, `txin`, `utxo` or `tx_raw_output` need to be specified."
            )

        utxo_dict = json.loads(self.query_cli(cli_args))
        return txtools.get_utxo(utxo_dict=utxo_dict, address=address_single, coins=coins)

    def get_tip(self) -> dict:
        """Return current tip - last block successfully applied to the ledger."""
        tip: dict = json.loads(self.query_cli(["tip"]))
        return tip

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
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        self.cli(
            [
                "genesis",
                "initial-addr",
                *self.magic_args,
                "--verification-key-file",
                str(vkey_file),
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return helpers.read_address_from_file(out_file)

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
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        if payment_vkey_file:
            cli_args = ["--payment-verification-key-file", str(payment_vkey_file)]
        elif payment_script_file:  # noqa: SIM106
            cli_args = ["--payment-script-file", str(payment_script_file)]
        else:
            raise AssertionError("Either `payment_vkey_file` or `payment_script_file` is needed.")

        if stake_vkey_file:
            cli_args.extend(["--stake-verification-key-file", str(stake_vkey_file)])
        elif stake_script_file:
            cli_args.extend(["--stake-script-file", str(stake_script_file)])

        self.cli(
            [
                "address",
                "build",
                *self.magic_args,
                *cli_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return helpers.read_address_from_file(out_file)

    def gen_stake_addr(
        self,
        addr_name: str,
        stake_vkey_file: Optional[FileType] = None,
        stake_script_file: Optional[FileType] = None,
        destination_dir: FileType = ".",
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
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{addr_name}_stake.addr"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        if stake_vkey_file:
            cli_args = ["--stake-verification-key-file", str(stake_vkey_file)]
        elif stake_script_file:  # noqa: SIM106
            cli_args = ["--stake-script-file", str(stake_script_file)]
        else:
            raise AssertionError("Either `stake_vkey_file` or `stake_script_file` is needed.")

        self.cli(
            [
                "stake-address",
                "build",
                *cli_args,
                *self.magic_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return helpers.read_address_from_file(out_file)

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
        clusterlib_helpers._check_files_exist(vkey, skey, clusterlib_obj=self)

        extended_args = ["--extended-key"] if extended else []

        self.cli(
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

    def gen_stake_key_pair(self, key_name: str, destination_dir: FileType = ".") -> structs.KeyPair:
        """Generate a stake address key pair.

        Args:
            key_name: A name of the key pair.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            structs.KeyPair: A tuple containing the key pair.
        """
        destination_dir = Path(destination_dir).expanduser()
        vkey = destination_dir / f"{key_name}_stake.vkey"
        skey = destination_dir / f"{key_name}_stake.skey"
        clusterlib_helpers._check_files_exist(vkey, skey, clusterlib_obj=self)

        self.cli(
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

    def gen_stake_addr_and_keys(
        self, name: str, destination_dir: FileType = "."
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
        clusterlib_helpers._check_files_exist(vkey, skey, clusterlib_obj=self)

        self.cli(
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
        clusterlib_helpers._check_files_exist(vkey, skey, clusterlib_obj=self)

        self.cli(
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
        clusterlib_helpers._check_files_exist(vkey, skey, counter, clusterlib_obj=self)

        self.cli(
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
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        kes_period = kes_period if kes_period is not None else self.get_kes_period()

        self.cli(
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

    def gen_stake_addr_registration_cert(
        self,
        addr_name: str,
        stake_vkey_file: Optional[FileType] = None,
        stake_script_file: Optional[FileType] = None,
        destination_dir: FileType = ".",
    ) -> Path:
        """Generate a stake address registration certificate.

        Args:
            addr_name: A name of stake address.
            stake_vkey_file: A path to corresponding stake vkey file (optional).
            stake_script_file: A path to corresponding payment script file (optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated certificate.
        """
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{addr_name}_stake_reg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        if stake_vkey_file:
            cli_args = ["--stake-verification-key-file", str(stake_vkey_file)]
        elif stake_script_file:  # noqa: SIM106
            cli_args = ["--stake-script-file", str(stake_script_file)]
        else:
            raise AssertionError("Either `stake_vkey_file` or `stake_script_file` is needed.")

        self.cli(
            [
                "stake-address",
                "registration-certificate",
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
        stake_vkey_file: Optional[FileType] = None,
        stake_script_file: Optional[FileType] = None,
        destination_dir: FileType = ".",
    ) -> Path:
        """Generate a stake address deregistration certificate.

        Args:
            addr_name: A name of stake address.
            stake_vkey_file: A path to corresponding stake vkey file (optional).
            stake_script_file: A path to corresponding payment script file (optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated certificate.
        """
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{addr_name}_stake_dereg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        if stake_vkey_file:
            cli_args = ["--stake-verification-key-file", str(stake_vkey_file)]
        elif stake_script_file:  # noqa: SIM106
            cli_args = ["--stake-script-file", str(stake_script_file)]
        else:
            raise AssertionError("Either `stake_vkey_file` or `stake_script_file` is needed.")

        self.cli(
            [
                "stake-address",
                "deregistration-certificate",
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
        stake_vkey_file: Optional[FileType] = None,
        stake_script_file: Optional[FileType] = None,
        cold_vkey_file: Optional[FileType] = None,
        stake_pool_id: str = "",
        destination_dir: FileType = ".",
    ) -> Path:
        """Generate a stake address delegation certificate.

        Args:
            addr_name: A name of stake address.
            stake_vkey_file: A path to corresponding stake vkey file (optional).
            stake_script_file: A path to corresponding payment script file (optional).
            cold_vkey_file: A path to pool cold vkey file (optional).
            stake_pool_id: An ID of the stake pool (optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated certificate.
        """
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{addr_name}_stake_deleg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        cli_args = []
        if stake_vkey_file:
            cli_args.extend(["--stake-verification-key-file", str(stake_vkey_file)])
        elif stake_script_file:  # noqa: SIM106
            cli_args.extend(["--stake-script-file", str(stake_script_file)])
        else:
            raise AssertionError("Either `stake_vkey_file` or `stake_script_file` is needed.")

        if cold_vkey_file:
            cli_args.extend(
                [
                    "--cold-verification-key-file",
                    str(cold_vkey_file),
                ]
            )
        elif stake_pool_id:  # noqa: SIM106
            cli_args.extend(
                [
                    "--stake-pool-id",
                    str(stake_pool_id),
                ]
            )
        else:
            raise AssertionError("Either `cold_vkey_file` or `stake_pool_id` is needed.")

        self.cli(
            [
                "stake-address",
                "delegation-certificate",
                *cli_args,
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def gen_pool_metadata_hash(self, pool_metadata_file: FileType) -> str:
        """Generate the hash of pool metadata.

        Args:
            pool_metadata_file: A path to the pool metadata file.

        Returns:
            str: A metadata hash.
        """
        return (
            self.cli(
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
            pool_data: A `structs.PoolData` tuple cointaining info about the stake pool.
            vrf_vkey_file: A path to node VRF vkey file.
            cold_vkey_file: A path to pool cold vkey file.
            owner_stake_vkey_files: A list of paths to pool owner stake vkey files.
            reward_account_vkey_file: A path to pool reward acount vkey file (optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated certificate.
        """
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{pool_data.pool_name}_pool_reg.cert"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

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

        self.cli(
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
                *self.magic_args,
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
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        self.cli(
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
            self.cli(
                ["address", "key-hash", "--payment-verification-key-file", str(payment_vkey_file)]
            )
            .stdout.rstrip()
            .decode("ascii")
        )

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
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        self.cli(
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
        """Generate a non extended key from a verification key.

        Args:
            key_name: A name of the key.
            extended_verification_key_file: A path to the extended verification key file.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the generated non extented verification key file.
        """
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{key_name}.vkey"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        self.cli(
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

    def get_ledger_state(self) -> dict:
        """Return the current ledger state info."""
        ledger_state: dict = json.loads(self.query_cli(["ledger-state"]))
        return ledger_state

    def save_ledger_state(
        self,
        state_name: str,
        destination_dir: FileType = ".",
    ) -> Path:
        """Save ledger state to file.

        Args:
            state_name: A name of the ledger state (can be epoch number, etc.).
            destination_dir: A path to directory for storing the state JSON file (optional).

        Returns:
            Path: A path to the generated state JSON file.
        """
        json_file = Path(destination_dir) / f"{state_name}_ledger_state.json"
        # TODO: workaround for https://github.com/input-output-hk/cardano-node/issues/2461
        # self.query_cli(["ledger-state", "--out-file", str(json_file)])
        ledger_state = self.get_ledger_state()
        with open(json_file, "w", encoding="utf-8") as fp_out:
            json.dump(ledger_state, fp_out, indent=4)
        return json_file

    def get_protocol_state(self) -> dict:
        """Return the current protocol state info."""
        protocol_state: dict = json.loads(self.query_cli(["protocol-state"]))
        return protocol_state

    def get_protocol_params(self) -> dict:
        """Return the current protocol parameters."""
        self.refresh_pparams_file()
        with open(self.pparams_file, encoding="utf-8") as in_json:
            pparams: dict = json.load(in_json)
        return pparams

    def get_registered_stake_pools_ledger_state(self) -> dict:
        """Return ledger state info for registered stake pools."""
        registered_pools_details: dict = self.get_ledger_state()["stateBefore"]["esLState"][
            "delegationState"
        ]["pstate"]["pParams pState"]
        return registered_pools_details

    def get_stake_pool_id(self, cold_vkey_file: FileType) -> str:
        """Return pool ID from the offline key.

        Args:
            cold_vkey_file: A path to pool cold vkey file.

        Returns:
            str: A pool ID.
        """
        pool_id = (
            self.cli(["stake-pool", "id", "--cold-verification-key-file", str(cold_vkey_file)])
            .stdout.strip()
            .decode("utf-8")
        )
        return pool_id

    def get_stake_snapshot(
        self,
        stake_pool_id: str,
    ) -> Dict[str, int]:
        """Return the three stake snapshots for a pool, plus the total active stake.

        Args:
            stake_pool_id: An ID of the stake pool (Bech32-encoded or hex-encoded).

        Returns:
            Dict: A stake snapshot data.
        """
        stake_snapshot: Dict[str, int] = json.loads(
            self.query_cli(["stake-snapshot", "--stake-pool-id", stake_pool_id])
        )
        return stake_snapshot

    def get_pool_params(
        self,
        stake_pool_id: str,
    ) -> structs.PoolParamsTop:
        """Return a pool parameters.

        Args:
            stake_pool_id: An ID of the stake pool (Bech32-encoded or hex-encoded).

        Returns:
            dict: A pool parameters.
        """
        pool_params: dict = json.loads(
            self.query_cli(["pool-params", "--stake-pool-id", stake_pool_id])
        )

        # in node 1.35.1+ the information is nested under hex encoded stake pool ID
        if "poolParams" not in pool_params:
            pool_params = next(iter(pool_params.values()))

        retiring = pool_params.get("retiring")  # pool retiring epoch
        pparams_top = structs.PoolParamsTop(
            pool_params=pool_params.get("poolParams") or {},
            future_pool_params=pool_params.get("futurePoolParams") or {},
            retiring=int(retiring) if retiring is not None else None,
        )
        return pparams_top

    def get_stake_addr_info(self, stake_addr: str) -> structs.StakeAddrInfo:
        """Return the current delegations and reward accounts filtered by stake address.

        Args:
            stake_addr: A stake address string.

        Returns:
            structs.StakeAddrInfo: A tuple containing stake address info.
        """
        output_json = json.loads(self.query_cli(["stake-address-info", "--address", stake_addr]))
        if not output_json:
            return structs.StakeAddrInfo(address="", delegation="", reward_account_balance=0)

        address_rec = list(output_json)[0]
        address = address_rec.get("address") or ""
        delegation = address_rec.get("delegation") or ""
        reward_account_balance = address_rec.get("rewardAccountBalance") or 0
        return structs.StakeAddrInfo(
            address=address,
            delegation=delegation,
            reward_account_balance=reward_account_balance,
        )

    def get_address_deposit(self) -> int:
        """Return stake address deposit amount."""
        pparams = self.get_protocol_params()
        return pparams.get("stakeAddressDeposit") or 0

    def get_pool_deposit(self) -> int:
        """Return stake pool deposit amount."""
        pparams = self.get_protocol_params()
        return pparams.get("stakePoolDeposit") or 0

    def get_stake_distribution(self) -> Dict[str, float]:
        """Return current aggregated stake distribution per stake pool."""
        # stake pool values are displayed starting with line 2 of the command output
        result = self.query_cli(["stake-distribution"]).splitlines()[2:]
        stake_distribution: Dict[str, float] = {}
        for pool in result:
            pool_id, stake = pool.split()
            stake_distribution[pool_id] = float(stake)
        return stake_distribution

    def get_stake_pools(self) -> List[str]:
        """Return the node's current set of stake pool ids."""
        stake_pools = self.query_cli(["stake-pools"]).splitlines()
        return stake_pools

    def get_leadership_schedule(
        self,
        vrf_skey_file: FileType,
        stake_pool_vkey: str = "",
        cold_vkey_file: Optional[FileType] = None,
        stake_pool_id: str = "",
        for_next: bool = False,
    ) -> List[structs.LeadershipSchedule]:
        """Get the slots the node is expected to mint a block in.

        Args:
            vrf_vkey_file: A path to node VRF vkey file.
            stake_pool_vkey: A pool cold vkey (Bech32 or hex-encoded, optional)
            cold_vkey_file: A path to pool cold vkey file (optional).
            stake_pool_id: An ID of the stake pool (Bech32 or hex-encoded, optional).
            for_next: A bool indicating whether to get the leadership schedule for the following
                epoch (current epoch by default)

        Returns:
            List[structs.LeadershipSchedule]: A list of `structs.LeadershipSchedule`, specifying
                slot and time.
        """
        args = []

        if stake_pool_vkey:
            args.extend(
                [
                    "--stake-pool-verification-key",
                    str(stake_pool_vkey),
                ]
            )
        elif cold_vkey_file:
            args.extend(
                [
                    "--cold-verification-key-file",
                    str(cold_vkey_file),
                ]
            )
        elif stake_pool_id:  # noqa: SIM106
            args.extend(
                [
                    "--stake-pool-id",
                    str(stake_pool_id),
                ]
            )
        else:
            raise AssertionError(
                "Either `stake_pool_vkey`, `cold_vkey_file` or `stake_pool_id` is needed."
            )

        args.append("--next" if for_next else "--current")

        unparsed = self.query_cli(
            [
                "leadership-schedule",
                "--genesis",
                str(self.genesis_json),
                "--vrf-signing-key-file",
                str(vrf_skey_file),
                *args,
            ]
            # schedule values are displayed starting with line 2 of the command output
        ).splitlines()[2:]

        schedule = []
        for rec in unparsed:
            slot_no, date_str, time_str, *__ = rec.split()
            # add miliseconds component of a time string if it is missing
            time_str = time_str if "." in time_str else f"{time_str}.0"
            schedule.append(
                structs.LeadershipSchedule(
                    slot_no=int(slot_no),
                    utc_time=datetime.datetime.strptime(
                        f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S.%f"
                    ),
                )
            )

        return schedule

    def get_slot_no(self) -> int:
        """Return slot number of last block that was successfully applied to the ledger."""
        return int(self.get_tip()["slot"])

    def get_block_no(self) -> int:
        """Return block number of last block that was successfully applied to the ledger."""
        return int(self.get_tip()["block"])

    def get_epoch(self) -> int:
        """Return epoch of last block that was successfully applied to the ledger."""
        return int(self.get_tip()["epoch"])

    def get_era(self) -> str:
        """Return network era."""
        era: str = self.get_tip()["era"]
        return era

    def get_address_balance(self, address: str, coin: str = consts.DEFAULT_COIN) -> int:
        """Get total balance of an address (sum of all UTxO balances).

        Args:
            address: A payment address string.
            coin: A coin name (asset IDs).

        Returns:
            int: A total balance.
        """
        utxo = self.get_utxo(address=address, coins=[coin])
        address_balance = functools.reduce(lambda x, y: x + y.amount, utxo, 0)
        return int(address_balance)

    def get_utxo_with_highest_amount(
        self, address: str, coin: str = consts.DEFAULT_COIN
    ) -> structs.UTXOData:
        """Return data for UTxO with highest amount.

        Args:
            address: A payment address string.
            coin: A coin name (asset IDs).

        Returns:
            structs.UTXOData: An UTxO record with the highest amount.
        """
        utxo = self.get_utxo(address=address, coins=[coin])
        highest_amount_rec = max(utxo, key=lambda x: x.amount)
        return highest_amount_rec

    def calculate_tx_ttl(self) -> int:
        """Calculate ttl for a transaction."""
        return self.get_slot_no() + self.ttl_length

    def get_kes_period(self) -> int:
        """Return last block KES period."""
        return int(self.get_slot_no() // self.slots_per_kes_period)

    def get_kes_period_info(self, opcert_file: FileType) -> dict:
        """Get information about the current KES period and node's operational certificate.

        Args:
            opcert_file: Operational certificate.

        Returns:
            dict: A dictionary containing KES period information.
        """
        command_output = self.query_cli(["kes-period-info", "--op-cert-file", str(opcert_file)])

        # get output messages
        messages_str = command_output.split("{")[0]
        messages_list = []

        valid_counters = False
        valid_kes_period = False

        if messages_str:
            message_entry: list = []

            for line in messages_str.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if not message_entry or line[0].isalpha():
                    message_entry.append(line)
                else:
                    messages_list.append(" ".join(message_entry))
                    message_entry = [line]

            messages_list.append(" ".join(message_entry))

            for out_message in messages_list:
                if "counter agrees with" in out_message:
                    valid_counters = True
                elif "correct KES period interval" in out_message:
                    valid_kes_period = True

        # get output metrics
        metrics_str = command_output.split("{")[-1]
        metrics_dict = {}

        if metrics_str and metrics_str.strip().endswith("}"):
            metrics_dict = json.loads(f"{{{metrics_str}")

        output_dict = {
            "messages": messages_list,
            "metrics": metrics_dict,
            "valid_counters": valid_counters,
            "valid_kes_period": valid_kes_period,
        }

        return output_dict

    def get_txid(self, tx_body_file: FileType = "", tx_file: FileType = "") -> str:
        """Return the transaction identifier.

        Args:
            tx_body_file: A path to the transaction body file (JSON TxBody - optional).
            tx_file: A path to the signed transaction file (JSON Tx - optional).

        Returns:
            str: A transaction ID.
        """
        if tx_body_file:
            cli_args = ["--tx-body-file", str(tx_body_file)]
        elif tx_file:  # noqa: SIM106
            cli_args = ["--tx-file", str(tx_file)]
        else:
            raise AssertionError("Either `tx_body_file` or `tx_file` is needed.")

        return self.cli(["transaction", "txid", *cli_args]).stdout.rstrip().decode("ascii")

    def view_tx(self, tx_body_file: FileType = "", tx_file: FileType = "") -> str:
        """View a transaction.

        Args:
            tx_body_file: A path to the transaction body file (JSON TxBody - optional).
            tx_file: A path to the signed transaction file (JSON Tx - optional).

        Returns:
            str: A transaction.
        """
        if tx_body_file:
            cli_args = ["--tx-body-file", str(tx_body_file)]
        elif tx_file:  # noqa: SIM106
            cli_args = ["--tx-file", str(tx_file)]
        else:
            raise AssertionError("Either `tx_body_file` or `tx_file` is needed.")

        return self.cli(["transaction", "view", *cli_args]).stdout.rstrip().decode("utf-8")

    def get_hash_script_data(
        self,
        script_data_file: Optional[FileType] = None,
        script_data_cbor_file: Optional[FileType] = None,
        script_data_value: str = "",
    ) -> str:
        """Return the hash of script data.

        Args:
            script_data_file: A path to the JSON file containing the script data (optional).
            script_data_cbor_file: A path to the CBOR file containing the script data (optional).
            script_data_value: A value (in JSON syntax) for the script data (optional).

        Returns:
            str: A hash of script data.
        """
        if script_data_file:
            cli_args = ["--script-data-file", str(script_data_file)]
        elif script_data_cbor_file:
            cli_args = ["--script-data-cbor-file", str(script_data_cbor_file)]
        elif script_data_value:  # noqa: SIM106
            cli_args = ["--script-data-value", str(script_data_value)]
        else:
            raise AssertionError(
                "Either `script_data_file`, `script_data_cbor_file` or `script_data_value` "
                "is needed."
            )

        return (
            self.cli(["transaction", "hash-script-data", *cli_args]).stdout.rstrip().decode("ascii")
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
            self.cli(["address", "info", "--address", str(address)]).stdout.rstrip().decode("utf-8")
        )
        return structs.AddressInfo(**addr_dict)

    def get_tx_deposit(self, tx_files: structs.TxFiles) -> int:
        """Get deposit amount for a transaction (based on certificates used for the TX).

        Args:
            tx_files: A `structs.TxFiles` tuple containing files needed for the transaction.

        Returns:
            int: A total deposit amount needed for the transaction.
        """
        if not tx_files.certificate_files:
            return 0

        pparams = self.get_protocol_params()
        key_deposit = pparams.get("stakeAddressDeposit") or 0
        pool_deposit = pparams.get("stakePoolDeposit") or 0

        deposit = 0
        for cert in tx_files.certificate_files:
            with open(cert, encoding="utf-8") as in_json:
                content = json.load(in_json)
            description = content.get("description", "")
            if "Stake Address Registration" in description:
                deposit += key_deposit
            elif "Stake Pool Registration" in description:
                deposit += pool_deposit
            elif "Stake Address Deregistration" in description:
                deposit -= key_deposit

        return deposit

    def get_tx_ins_outs(
        self,
        src_address: str,
        tx_files: structs.TxFiles,
        txins: structs.OptionalUTXOData = (),
        txouts: structs.OptionalTxOuts = (),
        fee: int = 0,
        deposit: Optional[int] = None,
        withdrawals: structs.OptionalTxOuts = (),
        mint_txouts: structs.OptionalTxOuts = (),
        lovelace_balanced: bool = False,
    ) -> Tuple[List[structs.UTXOData], List[structs.TxOut]]:
        """Return list of transaction's inputs and outputs.

        Args:
            src_address: An address used for fee and inputs (if inputs not specified by `txins`).
            tx_files: A `structs.TxFiles` tuple containing files needed for the transaction.
            txins: An iterable of `structs.UTXOData`, specifying input UTxOs (optional).
            txouts: A list (iterable) of `TxOuts`, specifying transaction outputs (optional).
            fee: A fee amount (optional).
            deposit: A deposit amount needed by the transaction (optional).
            withdrawals: A list (iterable) of `TxOuts`, specifying reward withdrawals (optional).
            mint_txouts: A list (iterable) of `TxOuts`, specifying minted tokens (optional).

        Returns:
            Tuple[list, list]: A tuple of list of transaction inputs and list of transaction
                outputs.
        """
        return txtools._get_tx_ins_outs(
            clusterlib_obj=self,
            src_address=src_address,
            tx_files=tx_files,
            txins=txins,
            txouts=txouts,
            fee=fee,
            deposit=deposit,
            withdrawals=withdrawals,
            mint_txouts=mint_txouts,
            lovelace_balanced=lovelace_balanced,
        )

    def build_raw_tx_bare(  # noqa: C901
        self,
        out_file: FileType,
        txouts: List[structs.TxOut],
        tx_files: structs.TxFiles,
        fee: int,
        txins: structs.OptionalUTXOData = (),
        readonly_reference_txins: structs.OptionalUTXOData = (),
        script_txins: structs.OptionalScriptTxIn = (),
        return_collateral_txouts: structs.OptionalTxOuts = (),
        total_collateral_amount: Optional[int] = None,
        mint: structs.OptionalMint = (),
        complex_certs: structs.OptionalScriptCerts = (),
        required_signers: OptionalFiles = (),
        required_signer_hashes: Optional[List[str]] = None,
        ttl: Optional[int] = None,
        withdrawals: structs.OptionalTxOuts = (),
        script_withdrawals: structs.OptionalScriptWithdrawals = (),
        invalid_hereafter: Optional[int] = None,
        invalid_before: Optional[int] = None,
        script_valid: bool = True,
        join_txouts: bool = True,
    ) -> structs.TxRawOutput:
        """Build a raw transaction.

        Args:
            out_file: An output file.
            txouts: A list (iterable) of `TxOuts`, specifying transaction outputs.
            tx_files: A `structs.TxFiles` tuple containing files needed for the transaction.
            fee: A fee amount.
            txins: An iterable of `structs.UTXOData`, specifying input UTxOs (optional).
            readonly_reference_txins: An iterable of `structs.UTXOData`, specifying input
                UTxOs to be referenced and used as readonly (optional).
            script_txins: An iterable of `ScriptTxIn`, specifying input script UTxOs (optional).
            return_collateral_txouts: A list (iterable) of `TxOuts`, specifying transaction outputs
                for excess collateral (optional).
            total_collateral_amount: An integer indicating the total amount of collateral
                (optional).
            mint: An iterable of `Mint`, specifying script minting data (optional).
            complex_certs: An iterable of `ComplexCert`, specifying certificates script data
                (optional).
            required_signers: An iterable of filepaths of the signing keys whose signatures
                are required (optional).
            required_signer_hashes: A list of hashes of the signing keys whose signatures
                are required (optional).
            ttl: A last block when the transaction is still valid
                (deprecated in favor of `invalid_hereafter`, optional).
            withdrawals: A list (iterable) of `TxOuts`, specifying reward withdrawals (optional).
            script_withdrawals: An iterable of `ScriptWithdrawal`, specifying withdrawal script
                data (optional).
            invalid_hereafter: A last block when the transaction is still valid (optional).
            invalid_before: A first block when the transaction is valid (optional).
            script_valid: A bool indicating that the script is valid (True by default).
            join_txouts: A bool indicating whether to aggregate transaction outputs
                by payment address (True by default).

        Returns:
            structs.TxRawOutput: A tuple with transaction output details.
        """
        # pylint: disable=too-many-arguments,too-many-branches,too-many-locals,too-many-statements
        if tx_files.certificate_files and complex_certs:
            LOGGER.warning(
                "Mixing `tx_files.certificate_files` and `complex_certs`, "
                "certs may come in unexpected order."
            )

        out_file = Path(out_file)

        withdrawals, script_withdrawals, withdrawals_txouts = txtools._get_withdrawals(
            clusterlib_obj=self, withdrawals=withdrawals, script_withdrawals=script_withdrawals
        )

        required_signer_hashes = required_signer_hashes or []
        txout_args = txtools._process_txouts(txouts=txouts, join_txouts=join_txouts)

        # filter out duplicates
        txins_combined = {f"{x.utxo_hash}#{x.utxo_ix}" for x in txins}
        withdrawals_combined = {f"{x.address}+{x.amount}" for x in withdrawals}

        mint_txouts = list(itertools.chain.from_iterable(m.txouts for m in mint))

        cli_args = []

        if invalid_before is not None:
            cli_args.extend(["--invalid-before", str(invalid_before)])
        if invalid_hereafter is not None:
            cli_args.extend(["--invalid-hereafter", str(invalid_hereafter)])
        elif ttl is not None:
            # `--ttl` and `--invalid-hereafter` are the same
            cli_args.extend(["--ttl", str(ttl)])

        if not script_valid:
            cli_args.append("--script-invalid")

        # only single `--mint` argument is allowed, let's aggregate all the outputs
        mint_records = [f"{m.amount} {m.coin}" for m in mint_txouts]
        cli_args.extend(["--mint", "+".join(mint_records)] if mint_records else [])

        for txin in readonly_reference_txins:
            cli_args.extend(["--read-only-tx-in-reference", f"{txin.utxo_hash}#{txin.utxo_ix}"])

        grouped_args = txtools._get_script_args(
            script_txins=script_txins,
            mint=mint,
            complex_certs=complex_certs,
            script_withdrawals=script_withdrawals,
            for_build=False,
        )

        grouped_args_str = " ".join(grouped_args)
        pparams_for_txins = grouped_args and (
            "-datum-" in grouped_args_str or "-redeemer-" in grouped_args_str
        )
        # TODO: see https://github.com/input-output-hk/cardano-node/issues/4058
        pparams_for_txouts = "datum-embed-" in " ".join(txout_args)
        if pparams_for_txins or pparams_for_txouts:
            self.create_pparams_file()
            grouped_args.extend(
                [
                    "--protocol-params-file",
                    str(self.pparams_file),
                ]
            )

        if total_collateral_amount:
            cli_args.extend(["--tx-total-collateral", str(total_collateral_amount)])

        cli_args.extend(["--cddl-format"] if self.use_cddl else [])

        self.cli(
            [
                "transaction",
                "build-raw",
                "--fee",
                str(fee),
                "--out-file",
                str(out_file),
                *grouped_args,
                *helpers._prepend_flag("--tx-in", txins_combined),
                *txout_args,
                *helpers._prepend_flag("--required-signer", required_signers),
                *helpers._prepend_flag("--required-signer-hash", required_signer_hashes),
                *helpers._prepend_flag("--certificate-file", tx_files.certificate_files),
                *helpers._prepend_flag("--update-proposal-file", tx_files.proposal_files),
                *helpers._prepend_flag("--auxiliary-script-file", tx_files.auxiliary_script_files),
                *helpers._prepend_flag("--metadata-json-file", tx_files.metadata_json_files),
                *helpers._prepend_flag("--metadata-cbor-file", tx_files.metadata_cbor_files),
                *helpers._prepend_flag("--withdrawal", withdrawals_combined),
                *txtools._get_return_collateral_txout_args(txouts=return_collateral_txouts),
                *cli_args,
                *self.tx_era_arg,
            ]
        )

        return structs.TxRawOutput(
            txins=list(txins),
            script_txins=script_txins,
            script_withdrawals=script_withdrawals,
            complex_certs=complex_certs,
            mint=mint,
            txouts=txouts,
            tx_files=tx_files,
            out_file=out_file,
            fee=fee,
            invalid_hereafter=invalid_hereafter or ttl,
            invalid_before=invalid_before,
            withdrawals=withdrawals_txouts,
            era=self.tx_era,
            return_collateral_txouts=return_collateral_txouts,
            total_collateral_amount=total_collateral_amount,
            readonly_reference_txins=readonly_reference_txins,
        )

    def build_raw_tx(
        self,
        src_address: str,
        tx_name: str,
        txins: structs.OptionalUTXOData = (),
        txouts: structs.OptionalTxOuts = (),
        readonly_reference_txins: structs.OptionalUTXOData = (),
        script_txins: structs.OptionalScriptTxIn = (),
        return_collateral_txouts: structs.OptionalTxOuts = (),
        total_collateral_amount: Optional[int] = None,
        mint: structs.OptionalMint = (),
        tx_files: Optional[structs.TxFiles] = None,
        complex_certs: structs.OptionalScriptCerts = (),
        fee: int = 0,
        ttl: Optional[int] = None,
        withdrawals: structs.OptionalTxOuts = (),
        script_withdrawals: structs.OptionalScriptWithdrawals = (),
        deposit: Optional[int] = None,
        invalid_hereafter: Optional[int] = None,
        invalid_before: Optional[int] = None,
        join_txouts: bool = True,
        destination_dir: FileType = ".",
    ) -> structs.TxRawOutput:
        """Balance inputs and outputs and build a raw transaction.

        Args:
            src_address: An address used for fee and inputs (if inputs not specified by `txins`).
            tx_name: A name of the transaction.
            txins: An iterable of `structs.UTXOData`, specifying input UTxOs (optional).
            txouts: A list (iterable) of `TxOuts`, specifying transaction outputs (optional).
            readonly_reference_txins: An iterable of `structs.UTXOData`, specifying input
                UTxOs to be referenced and used as readonly (optional).
            script_txins: An iterable of `ScriptTxIn`, specifying input script UTxOs (optional).
            return_collateral_txouts: A list (iterable) of `TxOuts`, specifying transaction outputs
                for excess collateral (optional).
            total_collateral_amount: An integer indicating the total amount of collateral
                (optional).
            mint: An iterable of `Mint`, specifying script minting data (optional).
            tx_files: A `structs.TxFiles` tuple containing files needed for the transaction
                (optional).
            complex_certs: An iterable of `ComplexCert`, specifying certificates script data
                (optional).
            fee: A fee amount (optional).
            ttl: A last block when the transaction is still valid
                (deprecated in favor of `invalid_hereafter`, optional).
            withdrawals: A list (iterable) of `TxOuts`, specifying reward withdrawals (optional).
            script_withdrawals: An iterable of `ScriptWithdrawal`, specifying withdrawal script
                data (optional).
            deposit: A deposit amount needed by the transaction (optional).
            invalid_hereafter: A last block when the transaction is still valid (optional).
            invalid_before: A first block when the transaction is valid (optional).
            join_txouts: A bool indicating whether to aggregate transaction outputs
                by payment address (True by default).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            structs.TxRawOutput: A tuple with transaction output details.
        """
        # pylint: disable=too-many-arguments
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{tx_name}_tx.body"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        tx_files = tx_files or structs.TxFiles()
        if ttl is None and invalid_hereafter is None and self.tx_era == consts.Eras.SHELLEY:
            invalid_hereafter = self.calculate_tx_ttl()

        withdrawals, script_withdrawals, withdrawals_txouts = txtools._get_withdrawals(
            clusterlib_obj=self, withdrawals=withdrawals, script_withdrawals=script_withdrawals
        )

        # combine txins and make sure we have enough funds to satisfy all txouts
        combined_txins = [
            *txins,
            *itertools.chain.from_iterable(r.txins for r in script_txins),
        ]
        mint_txouts = list(itertools.chain.from_iterable(m.txouts for m in mint))
        combined_tx_files = tx_files._replace(
            certificate_files=[
                *tx_files.certificate_files,
                *[c.certificate_file for c in complex_certs],
            ]
        )
        txins_copy, txouts_copy = self.get_tx_ins_outs(
            src_address=src_address,
            tx_files=combined_tx_files,
            txins=combined_txins,
            txouts=txouts,
            fee=fee,
            deposit=deposit,
            withdrawals=withdrawals_txouts,
            mint_txouts=mint_txouts,
        )

        tx_raw_output = self.build_raw_tx_bare(
            out_file=out_file,
            txouts=txouts_copy,
            tx_files=tx_files,
            fee=fee,
            txins=txins or txins_copy,
            readonly_reference_txins=readonly_reference_txins,
            script_txins=script_txins,
            return_collateral_txouts=return_collateral_txouts,
            total_collateral_amount=total_collateral_amount,
            mint=mint,
            withdrawals=withdrawals,
            script_withdrawals=script_withdrawals,
            invalid_hereafter=invalid_hereafter or ttl,
            invalid_before=invalid_before,
            join_txouts=join_txouts,
        )

        helpers._check_outfiles(out_file)
        return tx_raw_output

    def estimate_fee(
        self,
        txbody_file: FileType,
        txin_count: int,
        txout_count: int,
        witness_count: int = 1,
        byron_witness_count: int = 0,
    ) -> int:
        """Estimate the minimum fee for a transaction.

        Args:
            txbody_file: A path to file with transaction body.
            txin_count: A number of transaction inputs.
            txout_count: A number of transaction outputs.
            witness_count: A number of witnesses (optional).
            byron_witness_count: A number of Byron witnesses (optional).

        Returns:
            int: An estimated fee.
        """
        self.create_pparams_file()
        stdout = self.cli(
            [
                "transaction",
                "calculate-min-fee",
                *self.magic_args,
                "--protocol-params-file",
                str(self.pparams_file),
                "--tx-in-count",
                str(txin_count),
                "--tx-out-count",
                str(txout_count),
                "--byron-witness-count",
                str(byron_witness_count),
                "--witness-count",
                str(witness_count),
                "--tx-body-file",
                str(txbody_file),
            ]
        ).stdout
        fee, *__ = stdout.decode().split()
        return int(fee)

    def calculate_tx_fee(
        self,
        src_address: str,
        tx_name: str,
        dst_addresses: Optional[List[str]] = None,
        txins: structs.OptionalUTXOData = (),
        txouts: structs.OptionalTxOuts = (),
        readonly_reference_txins: structs.OptionalUTXOData = (),
        script_txins: structs.OptionalScriptTxIn = (),
        return_collateral_txouts: structs.OptionalTxOuts = (),
        total_collateral_amount: Optional[int] = None,
        mint: structs.OptionalMint = (),
        tx_files: Optional[structs.TxFiles] = None,
        complex_certs: structs.OptionalScriptCerts = (),
        ttl: Optional[int] = None,
        withdrawals: structs.OptionalTxOuts = (),
        script_withdrawals: structs.OptionalScriptWithdrawals = (),
        invalid_hereafter: Optional[int] = None,
        invalid_before: Optional[int] = None,
        witness_count_add: int = 0,
        join_txouts: bool = True,
        destination_dir: FileType = ".",
    ) -> int:
        """Build "dummy" transaction and calculate (estimate) its fee.

        Args:
            src_address: An address used for fee and inputs (if inputs not specified by `txins`).
            tx_name: A name of the transaction.
            dst_addresses: A list of destination addresses (optional)
            txins: An iterable of `structs.UTXOData`, specifying input UTxOs (optional).
            txouts: A list (iterable) of `TxOuts`, specifying transaction outputs (optional).
            readonly_reference_txins: An iterable of `structs.UTXOData`, specifying input
                UTxOs to be referenced and used as readonly (optional).
            script_txins: An iterable of `ScriptTxIn`, specifying input script UTxOs (optional).
            return_collateral_txouts: A list (iterable) of `TxOuts`, specifying transaction outputs
                for excess collateral (optional).
            total_collateral_amount: An integer indicating the total amount of collateral
                (optional).
            mint: An iterable of `Mint`, specifying script minting data (optional).
            tx_files: A `structs.TxFiles` tuple containing files needed for the transaction
                (optional).
            complex_certs: An iterable of `ComplexCert`, specifying certificates script data
                (optional).
            ttl: A last block when the transaction is still valid
                (deprecated in favor of `invalid_hereafter`, optional).
            withdrawals: A list (iterable) of `TxOuts`, specifying reward withdrawals (optional).
            script_withdrawals: An iterable of `ScriptWithdrawal`, specifying withdrawal script
                data (optional).
            invalid_hereafter: A last block when the transaction is still valid (optional).
            invalid_before: A first block when the transaction is valid (optional).
            witness_count_add: A number of witnesses to add - workaround to make the fee
                calculation more precise.
            join_txouts: A bool indicating whether to aggregate transaction outputs
                by payment address (True by default).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            int: An estimated fee.
        """
        # pylint: disable=too-many-arguments
        tx_files = tx_files or structs.TxFiles()
        tx_name = f"{tx_name}_estimate"

        if dst_addresses and txouts:
            LOGGER.warning(
                "The value of `dst_addresses` is ignored when value for `txouts` is available."
            )

        txouts_filled = txouts or [
            structs.TxOut(address=r, amount=1) for r in (dst_addresses or ())
        ]

        tx_raw_output = self.build_raw_tx(
            src_address=src_address,
            tx_name=tx_name,
            txins=txins,
            txouts=txouts_filled,
            readonly_reference_txins=readonly_reference_txins,
            script_txins=script_txins,
            return_collateral_txouts=return_collateral_txouts,
            total_collateral_amount=total_collateral_amount,
            mint=mint,
            tx_files=tx_files,
            complex_certs=complex_certs,
            fee=0,
            withdrawals=withdrawals,
            script_withdrawals=script_withdrawals,
            invalid_hereafter=invalid_hereafter or ttl,
            invalid_before=invalid_before,
            deposit=0,
            join_txouts=join_txouts,
            destination_dir=destination_dir,
        )

        fee = self.estimate_fee(
            txbody_file=tx_raw_output.out_file,
            # +1 as possibly one more input will be needed for the fee amount
            txin_count=len(tx_raw_output.txins) + 1,
            txout_count=len(tx_raw_output.txouts),
            witness_count=len(tx_files.signing_key_files) + witness_count_add,
        )

        return fee

    def calculate_min_value(
        self,
        multi_assets: List[structs.TxOut],
    ) -> structs.Value:
        """Calculate the minimum value in for a transaction.

        This was replaced by `calculate_min_req_utxo` for node 1.29.0+.

        Args:
            multi_assets: A list of `TxOuts`, specifying multi-assets.

        Returns:
            structs.Value: A tuple describing the value.
        """
        warnings.warn("deprecated by `calculate_min_req_utxo` for node 1.29.0+", DeprecationWarning)

        ma_records = [f"{m.amount} {m.coin}" for m in multi_assets]
        ma_args = ["--multi-asset", "+".join(ma_records)] if ma_records else []

        self.create_pparams_file()
        stdout = self.cli(
            [
                "transaction",
                "calculate-min-value",
                "--protocol-params-file",
                str(self.pparams_file),
                *ma_args,
            ]
        ).stdout
        coin, value = stdout.decode().split()
        return structs.Value(value=int(value), coin=coin)

    def calculate_min_req_utxo(
        self,
        txouts: List[structs.TxOut],
    ) -> structs.Value:
        """Calculate the minimum required UTxO for a single transaction output.

        Args:
            txouts: A list of `TxOut` records that correspond to a single transaction output (UTxO).

        Returns:
            structs.Value: A tuple describing the value.
        """
        if not txouts:
            raise AssertionError("No txout was specified.")

        addresses = {t.address for t in txouts}
        if len(addresses) > 1:
            raise AssertionError("Accepts `txouts` only for a single address.")

        txout_records = [
            f"{t.amount} {t.coin if t.coin != consts.DEFAULT_COIN else ''}".rstrip() for t in txouts
        ]
        # pylint: disable=consider-using-f-string
        address_value = "{}+{}".format(txouts[0].address, "+".join(txout_records))

        txout_args = txtools._get_txout_plutus_args(txout=txouts[0])

        era = self.get_era()
        era_arg = f"--{era.lower()}-era"

        self.create_pparams_file()
        stdout = self.cli(
            [
                "transaction",
                "calculate-min-required-utxo",
                "--protocol-params-file",
                str(self.pparams_file),
                era_arg,
                "--tx-out",
                address_value,
                *txout_args,
            ]
        ).stdout
        coin, value = stdout.decode().split()
        return structs.Value(value=int(value), coin=coin)

    def build_tx(  # noqa: C901
        self,
        src_address: str,
        tx_name: str,
        txins: structs.OptionalUTXOData = (),
        txouts: structs.OptionalTxOuts = (),
        readonly_reference_txins: structs.OptionalUTXOData = (),
        script_txins: structs.OptionalScriptTxIn = (),
        return_collateral_txouts: structs.OptionalTxOuts = (),
        total_collateral_amount: Optional[int] = None,
        mint: structs.OptionalMint = (),
        tx_files: Optional[structs.TxFiles] = None,
        complex_certs: structs.OptionalScriptCerts = (),
        change_address: str = "",
        fee_buffer: Optional[int] = None,
        required_signers: OptionalFiles = (),
        required_signer_hashes: Optional[List[str]] = None,
        withdrawals: structs.OptionalTxOuts = (),
        script_withdrawals: structs.OptionalScriptWithdrawals = (),
        deposit: Optional[int] = None,
        invalid_hereafter: Optional[int] = None,
        invalid_before: Optional[int] = None,
        witness_override: Optional[int] = None,
        script_valid: bool = True,
        calc_script_cost_file: Optional[FileType] = None,
        join_txouts: bool = True,
        destination_dir: FileType = ".",
    ) -> structs.TxRawOutput:
        """Build a transaction.

        Args:
            src_address: An address used for fee and inputs (if inputs not specified by `txins`).
            tx_name: A name of the transaction.
            txins: An iterable of `structs.UTXOData`, specifying input UTxOs (optional).
            txouts: A list (iterable) of `TxOuts`, specifying transaction outputs (optional).
            readonly_reference_txins: An iterable of `structs.UTXOData`, specifying input
                UTxOs to be referenced and used as readonly (optional).
            script_txins: An iterable of `ScriptTxIn`, specifying input script UTxOs (optional).
            return_collateral_txouts: A list (iterable) of `TxOuts`, specifying transaction outputs
                for excess collateral (optional).
            total_collateral_amount: An integer indicating the total amount of collateral
                (optional).
            mint: An iterable of `Mint`, specifying script minting data (optional).
            tx_files: A `structs.TxFiles` tuple containing files needed for the transaction
                (optional).
            complex_certs: An iterable of `ComplexCert`, specifying certificates script data
                (optional).
            change_address: A string with address where ADA in excess of the transaction fee
                will go to (`src_address` by default).
            fee_buffer: A buffer for fee amount (optional).
            required_signers: An iterable of filepaths of the signing keys whose signatures
                are required (optional).
            required_signer_hashes: A list of hashes of the signing keys whose signatures
                are required (optional).
            withdrawals: A list (iterable) of `TxOuts`, specifying reward withdrawals (optional).
            script_withdrawals: An iterable of `ScriptWithdrawal`, specifying withdrawal script
                data (optional).
            deposit: A deposit amount needed by the transaction (optional).
            invalid_hereafter: A last block when the transaction is still valid (optional).
            invalid_before: A first block when the transaction is valid (optional).
            witness_override: An integer indicating real number of witnesses. Can be used to fix
                fee calculation (optional).
            script_valid: A bool indicating that the script is valid (True by default).
            calc_script_cost_file: A path for output of the Plutus script cost information
                (optional).
            join_txouts: A bool indicating whether to aggregate transaction outputs
                by payment address (True by default).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            structs.TxRawOutput: A tuple with transaction output details.
        """
        # pylint: disable=too-many-arguments,too-many-locals,too-many-statements,too-many-branches
        max_txout = [o for o in txouts if o.amount == -1 and o.coin in ("", consts.DEFAULT_COIN)]
        if max_txout and change_address:
            raise AssertionError("Cannot use '-1' amount and change address at the same time.")

        tx_files = tx_files or structs.TxFiles()

        if tx_files.certificate_files and complex_certs:
            LOGGER.warning(
                "Mixing `tx_files.certificate_files` and `complex_certs`, "
                "certs may come in unexpected order."
            )

        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{tx_name}_tx.body"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        withdrawals, script_withdrawals, withdrawals_txouts = txtools._get_withdrawals(
            clusterlib_obj=self, withdrawals=withdrawals, script_withdrawals=script_withdrawals
        )

        required_signer_hashes = required_signer_hashes or []

        mint_txouts = list(itertools.chain.from_iterable(m.txouts for m in mint))

        # combine txins and make sure we have enough funds to satisfy all txouts
        combined_txins = [
            *txins,
            *itertools.chain.from_iterable(r.txins for r in script_txins),
        ]
        combined_tx_files = tx_files._replace(
            certificate_files=[
                *tx_files.certificate_files,
                *[c.certificate_file for c in complex_certs],
            ]
        )
        txins_copy, txouts_copy = self.get_tx_ins_outs(
            src_address=src_address,
            tx_files=combined_tx_files,
            txins=combined_txins,
            txouts=txouts,
            fee=fee_buffer or 0,
            deposit=deposit,
            withdrawals=withdrawals_txouts,
            mint_txouts=mint_txouts,
            lovelace_balanced=True,
        )

        txout_args = txtools._process_txouts(txouts=txouts_copy, join_txouts=join_txouts)

        # filter out duplicate txins
        txins_utxos = {f"{x.utxo_hash}#{x.utxo_ix}" for x in txins_copy}
        # assume that all plutus txin records are for the same UTxO and use the first one
        plutus_txins_utxos = {
            f"{x.txins[0].utxo_hash}#{x.txins[0].utxo_ix}" for x in script_txins if x.txins
        }
        txins_combined = txins_utxos.difference(plutus_txins_utxos)

        withdrawals_combined = [f"{x.address}+{x.amount}" for x in withdrawals]

        cli_args = []

        if invalid_before is not None:
            cli_args.extend(["--invalid-before", str(invalid_before)])
        if invalid_hereafter is not None:
            cli_args.extend(["--invalid-hereafter", str(invalid_hereafter)])

        if not script_valid:
            cli_args.append("--script-invalid")

        # there's allowed just single `--mint` argument, let's aggregate all the outputs
        mint_records = [f"{m.amount} {m.coin}" for m in mint_txouts]
        cli_args.extend(["--mint", "+".join(mint_records)] if mint_records else [])

        for txin in readonly_reference_txins:
            cli_args.extend(["--read-only-tx-in-reference", f"{txin.utxo_hash}#{txin.utxo_ix}"])

        grouped_args = txtools._get_script_args(
            script_txins=script_txins,
            mint=mint,
            complex_certs=complex_certs,
            script_withdrawals=script_withdrawals,
            for_build=True,
        )

        grouped_args_str = " ".join(grouped_args)
        pparams_for_txins = grouped_args and (
            "-datum-" in grouped_args_str or "-redeemer-" in grouped_args_str
        )
        # TODO: see https://github.com/input-output-hk/cardano-node/issues/4058
        pparams_for_txouts = "-embed-" in " ".join(txout_args)
        if pparams_for_txins or pparams_for_txouts:
            grouped_args.extend(
                [
                    "--protocol-params-file",
                    str(self.pparams_file),
                ]
            )

        cli_args.append("--change-address")
        if max_txout:
            cli_args.append(max_txout[0].address)
        elif change_address:
            cli_args.append(change_address)
        else:
            cli_args.append(src_address)

        if witness_override is not None:
            cli_args.extend(["--witness-override", str(witness_override)])

        if total_collateral_amount:
            cli_args.extend(["--tx-total-collateral", str(total_collateral_amount)])

        cli_args.extend(["--cddl-format"] if self.use_cddl else [])

        if calc_script_cost_file:
            cli_args.extend(["--calculate-plutus-script-cost", str(calc_script_cost_file)])
            out_file = Path(calc_script_cost_file)
        else:
            cli_args.extend(["--out-file", str(out_file)])

        stdout = self.cli(
            [
                "transaction",
                "build",
                *grouped_args,
                *helpers._prepend_flag("--tx-in", txins_combined),
                *txout_args,
                *helpers._prepend_flag("--required-signer", required_signers),
                *helpers._prepend_flag("--required-signer-hash", required_signer_hashes),
                *helpers._prepend_flag("--certificate-file", tx_files.certificate_files),
                *helpers._prepend_flag("--update-proposal-file", tx_files.proposal_files),
                *helpers._prepend_flag("--auxiliary-script-file", tx_files.auxiliary_script_files),
                *helpers._prepend_flag("--metadata-json-file", tx_files.metadata_json_files),
                *helpers._prepend_flag("--metadata-cbor-file", tx_files.metadata_cbor_files),
                *helpers._prepend_flag("--withdrawal", withdrawals_combined),
                *txtools._get_return_collateral_txout_args(txouts=return_collateral_txouts),
                *cli_args,
                *self.tx_era_arg,
                *self.magic_args,
            ]
        ).stdout
        stdout_dec = stdout.decode("utf-8") if stdout else ""

        # check for the presence of fee information so compatibility with older versions
        # of the `build` command is preserved
        estimated_fee = -1
        if "transaction fee" in stdout_dec:
            estimated_fee = int(stdout_dec.split()[-1])

        return structs.TxRawOutput(
            txins=list(txins_copy),
            script_txins=script_txins,
            script_withdrawals=script_withdrawals,
            complex_certs=complex_certs,
            mint=mint,
            txouts=list(txouts_copy),
            tx_files=tx_files,
            out_file=out_file,
            fee=estimated_fee,
            invalid_hereafter=invalid_hereafter,
            invalid_before=invalid_before,
            withdrawals=withdrawals_txouts,
            change_address=change_address or src_address,
            era=self.tx_era,
            return_collateral_txouts=return_collateral_txouts,
            total_collateral_amount=total_collateral_amount,
            readonly_reference_txins=readonly_reference_txins,
        )

    def sign_tx(
        self,
        signing_key_files: OptionalFiles,
        tx_name: str,
        tx_body_file: Optional[FileType] = None,
        tx_file: Optional[FileType] = None,
        destination_dir: FileType = ".",
    ) -> Path:
        """Sign a transaction.

        Args:
            signing_key_files: A list of paths to signing key files.
            tx_name: A name of the transaction.
            tx_body_file: A path to file with transaction body (optional).
            tx_file: A path to file with transaction (for incremental signing, optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to signed transaction file.
        """
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{tx_name}_tx.signed"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        if tx_body_file:
            cli_args = ["--tx-body-file", str(tx_body_file)]
        elif tx_file:  # noqa: SIM106
            cli_args = ["--tx-file", str(tx_file)]
        else:
            raise AssertionError("Either `tx_body_file` or `tx_file` is needed.")

        self.cli(
            [
                "transaction",
                "sign",
                *cli_args,
                *self.magic_args,
                *helpers._prepend_flag("--signing-key-file", signing_key_files),
                "--out-file",
                str(out_file),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def witness_tx(
        self,
        tx_body_file: FileType,
        witness_name: str,
        signing_key_files: OptionalFiles = (),
        destination_dir: FileType = ".",
    ) -> Path:
        """Create a transaction witness.

        Args:
            tx_body_file: A path to file with transaction body.
            witness_name: A name of the transaction witness.
            signing_key_files: A list of paths to signing key files (optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to transaction witness file.
        """
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{witness_name}_tx.witness"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        self.cli(
            [
                "transaction",
                "witness",
                "--tx-body-file",
                str(tx_body_file),
                "--out-file",
                str(out_file),
                *self.magic_args,
                *helpers._prepend_flag("--signing-key-file", signing_key_files),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def assemble_tx(
        self,
        tx_body_file: FileType,
        witness_files: OptionalFiles,
        tx_name: str,
        destination_dir: FileType = ".",
    ) -> Path:
        """Assemble a tx body and witness(es) to form a signed transaction.

        Args:
            tx_body_file: A path to file with transaction body.
            witness_files: A list of paths to transaction witness files.
            tx_name: A name of the transaction.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to signed transaction file.
        """
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{tx_name}_tx.witnessed"
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        self.cli(
            [
                "transaction",
                "assemble",
                "--tx-body-file",
                str(tx_body_file),
                "--out-file",
                str(out_file),
                *helpers._prepend_flag("--witness-file", witness_files),
            ]
        )

        helpers._check_outfiles(out_file)
        return out_file

    def submit_tx_bare(self, tx_file: FileType) -> None:
        """Submit a transaction, don't do any verification that it made it to the chain.

        Args:
            tx_file: A path to signed transaction file.
        """
        self.cli(
            [
                "transaction",
                "submit",
                *self.magic_args,
                "--tx-file",
                str(tx_file),
                f"--{self.protocol}-mode",
            ]
        )

    def submit_tx(
        self, tx_file: FileType, txins: List[structs.UTXOData], wait_blocks: int = 2
    ) -> None:
        """Submit a transaction, resubmit if the transaction didn't make it to the chain.

        Args:
            tx_file: A path to signed transaction file.
            txins: An iterable of `structs.UTXOData`, specifying input UTxOs.
            wait_blocks: A number of new blocks to wait for (default = 2).
        """
        txid = ""
        err = None
        for r in range(3):
            if r == 0:
                self.submit_tx_bare(tx_file)
                self.wait_for_new_block(wait_blocks)
            else:
                txid = txid or self.get_txid(tx_file=tx_file)
                LOGGER.info(f"Resubmitting transaction '{txid}' (from '{tx_file}').")
                try:
                    self.submit_tx_bare(tx_file)
                except exceptions.CLIError as exc:
                    # check if resubmitting failed because an input UTxO was already spent
                    if "(BadInputsUTxO" not in str(exc):
                        raise
                    err = exc
                else:
                    self.wait_for_new_block(wait_blocks)

            # Check that one of the input UTxOs was spent to verify the TX was
            # successfully submitted to the chain.
            # An input is spent when its combination of hash and ix is not found in the list
            # of current UTxOs.
            # TODO: check that the transaction is 1-block deep (can't be done in CLI alone)
            utxo_data = self.get_utxo(utxo=txins[0])

            if not utxo_data:
                break
            if err is not None:
                # Submitting the TX raised an exception as if the input was already
                # spent, but it was not the case. Reraising the exception.
                raise err
        else:
            raise exceptions.CLIError(
                f"Transaction '{txid}' didn't make it to the chain (from '{tx_file}')."
            )

    def send_tx(
        self,
        src_address: str,
        tx_name: str,
        txins: structs.OptionalUTXOData = (),
        txouts: structs.OptionalTxOuts = (),
        readonly_reference_txins: structs.OptionalUTXOData = (),
        script_txins: structs.OptionalScriptTxIn = (),
        return_collateral_txouts: structs.OptionalTxOuts = (),
        total_collateral_amount: Optional[int] = None,
        mint: structs.OptionalMint = (),
        tx_files: Optional[structs.TxFiles] = None,
        complex_certs: structs.OptionalScriptCerts = (),
        fee: Optional[int] = None,
        ttl: Optional[int] = None,
        withdrawals: structs.OptionalTxOuts = (),
        script_withdrawals: structs.OptionalScriptWithdrawals = (),
        deposit: Optional[int] = None,
        invalid_hereafter: Optional[int] = None,
        invalid_before: Optional[int] = None,
        witness_count_add: int = 0,
        join_txouts: bool = True,
        verify_tx: bool = True,
        destination_dir: FileType = ".",
    ) -> structs.TxRawOutput:
        """Build, Sign and Submit a transaction.

        Args:
            src_address: An address used for fee and inputs (if inputs not specified by `txins`).
            tx_name: A name of the transaction.
            txins: An iterable of `structs.UTXOData`, specifying input UTxOs (optional).
            txouts: A list (iterable) of `TxOuts`, specifying transaction outputs (optional).
            readonly_reference_txins: An iterable of `structs.UTXOData`, specifying input
                UTxOs to be referenced and used as readonly (optional).
            script_txins: An iterable of `ScriptTxIn`, specifying input script UTxOs (optional).
            return_collateral_txouts: A list (iterable) of `TxOuts`, specifying transaction outputs
                for excess collateral (optional).
            total_collateral_amount: An integer indicating the total amount of collateral
                (optional).
            mint: An iterable of `Mint`, specifying script minting data (optional).
            tx_files: A `structs.TxFiles` tuple containing files needed for the transaction
                (optional).
            complex_certs: An iterable of `ComplexCert`, specifying certificates script data
                (optional).
            fee: A fee amount (optional).
            ttl: A last block when the transaction is still valid
                (deprecated in favor of `invalid_hereafter`, optional).
            withdrawals: A list (iterable) of `TxOuts`, specifying reward withdrawals (optional).
            script_withdrawals: An iterable of `ScriptWithdrawal`, specifying withdrawal script
                data (optional).
            deposit: A deposit amount needed by the transaction (optional).
            invalid_hereafter: A last block when the transaction is still valid (optional).
            invalid_before: A first block when the transaction is valid (optional).
            witness_count_add: A number of witnesses to add - workaround to make the fee
                calculation more precise.
            join_txouts: A bool indicating whether to aggregate transaction outputs
                by payment address (True by default).
            verify_tx: A bool indicating whether to verify the transaction made it to chain
                and resubmit the transaction if not (True by default).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            structs.TxRawOutput: A tuple with transaction output details.
        """
        # pylint: disable=too-many-arguments
        tx_files = tx_files or structs.TxFiles()

        withdrawals, script_withdrawals, *__ = txtools._get_withdrawals(
            clusterlib_obj=self, withdrawals=withdrawals, script_withdrawals=script_withdrawals
        )

        if fee is None:
            fee = self.calculate_tx_fee(
                src_address=src_address,
                tx_name=tx_name,
                txins=txins,
                txouts=txouts,
                readonly_reference_txins=readonly_reference_txins,
                script_txins=script_txins,
                return_collateral_txouts=return_collateral_txouts,
                total_collateral_amount=total_collateral_amount,
                mint=mint,
                tx_files=tx_files,
                complex_certs=complex_certs,
                withdrawals=withdrawals,
                script_withdrawals=script_withdrawals,
                invalid_hereafter=invalid_hereafter or ttl,
                witness_count_add=witness_count_add,
                join_txouts=join_txouts,
                destination_dir=destination_dir,
            )

            # add 10% to the estimated fee, as the estimation is not precise enough
            fee = int(fee * 1.1)

        tx_raw_output = self.build_raw_tx(
            src_address=src_address,
            tx_name=tx_name,
            txins=txins,
            txouts=txouts,
            readonly_reference_txins=readonly_reference_txins,
            script_txins=script_txins,
            return_collateral_txouts=return_collateral_txouts,
            total_collateral_amount=total_collateral_amount,
            mint=mint,
            tx_files=tx_files,
            complex_certs=complex_certs,
            fee=fee,
            withdrawals=withdrawals,
            script_withdrawals=script_withdrawals,
            deposit=deposit,
            invalid_hereafter=invalid_hereafter or ttl,
            invalid_before=invalid_before,
            join_txouts=join_txouts,
            destination_dir=destination_dir,
        )
        tx_signed_file = self.sign_tx(
            tx_body_file=tx_raw_output.out_file,
            tx_name=tx_name,
            signing_key_files=tx_files.signing_key_files,
            destination_dir=destination_dir,
        )
        if verify_tx:
            self.submit_tx(
                tx_file=tx_signed_file,
                txins=tx_raw_output.txins
                or [t.txins[0] for t in tx_raw_output.script_txins if t.txins],
            )
        else:
            self.submit_tx_bare(tx_file=tx_signed_file)

        return tx_raw_output

    def build_multisig_script(
        self,
        script_name: str,
        script_type_arg: str,
        payment_vkey_files: OptionalFiles,
        required: int = 0,
        slot: int = 0,
        slot_type_arg: str = "",
        destination_dir: FileType = ".",
    ) -> Path:
        """Build a multi-signature script.

        Args:
            script_name: A name of the script.
            script_type_arg: A script type, see `MultiSigTypeArgs`.
            payment_vkey_files: A list of paths to payment vkey files.
            required: A number of required keys for the "atLeast" script type (optional).
            slot: A slot that sets script validity, depending on value of `slot_type_arg`
                (optional).
            slot_type_arg: A slot validity type, see `MultiSlotTypeArgs` (optional).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            Path: A path to the script file.
        """
        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{script_name}_multisig.script"

        scripts_l: List[dict] = [
            {"keyHash": self.get_payment_vkey_hash(f), "type": "sig"} for f in payment_vkey_files
        ]
        if slot:
            scripts_l.append({"slot": slot, "type": slot_type_arg})

        script: dict = {
            "scripts": scripts_l,
            "type": script_type_arg,
        }

        if script_type_arg == consts.MultiSigTypeArgs.AT_LEAST:
            script["required"] = required

        with open(out_file, "w", encoding="utf-8") as fp_out:
            json.dump(script, fp_out, indent=4)

        return out_file

    def get_policyid(
        self,
        script_file: FileType,
    ) -> str:
        """Calculate the PolicyId from the monetary policy script.

        Args:
            script_file: A path to the script file.

        Returns:
            str: A script policyId.
        """
        return (
            self.cli(["transaction", "policyid", "--script-file", str(script_file)])
            .stdout.rstrip()
            .decode("utf-8")
        )

    def calculate_plutus_script_cost(
        self,
        src_address: str,
        tx_name: str,
        txins: structs.OptionalUTXOData = (),
        txouts: structs.OptionalTxOuts = (),
        readonly_reference_txins: structs.OptionalUTXOData = (),
        script_txins: structs.OptionalScriptTxIn = (),
        return_collateral_txouts: structs.OptionalTxOuts = (),
        total_collateral_amount: Optional[int] = None,
        mint: structs.OptionalMint = (),
        tx_files: Optional[structs.TxFiles] = None,
        complex_certs: structs.OptionalScriptCerts = (),
        change_address: str = "",
        fee_buffer: Optional[int] = None,
        required_signers: OptionalFiles = (),
        required_signer_hashes: Optional[List[str]] = None,
        withdrawals: structs.OptionalTxOuts = (),
        script_withdrawals: structs.OptionalScriptWithdrawals = (),
        deposit: Optional[int] = None,
        invalid_hereafter: Optional[int] = None,
        invalid_before: Optional[int] = None,
        witness_override: Optional[int] = None,
        script_valid: bool = True,
        calc_script_cost_file: Optional[FileType] = None,
        join_txouts: bool = True,
        destination_dir: FileType = ".",
    ) -> List[dict]:
        """Calculate cost of Plutus scripts. Accepts the same arguments as `build_tx`.

        Args:
            src_address: An address used for fee and inputs (if inputs not specified by `txins`).
            tx_name: A name of the transaction.
            txins: An iterable of `structs.UTXOData`, specifying input UTxOs (optional).
            txouts: A list (iterable) of `TxOuts`, specifying transaction outputs (optional).
            readonly_reference_txins: An iterable of `structs.UTXOData`, specifying input
                UTxOs to be referenced and used as readonly (optional).
            script_txins: An iterable of `ScriptTxIn`, specifying input script UTxOs (optional).
            return_collateral_txouts: A list (iterable) of `TxOuts`, specifying transaction outputs
                for excess collateral (optional).
            total_collateral_amount: An integer indicating the total amount of collateral
                (optional).
            mint: An iterable of `Mint`, specifying script minting data (optional).
            tx_files: A `structs.TxFiles` tuple containing files needed for the transaction
                (optional).
            complex_certs: An iterable of `ComplexCert`, specifying certificates script data
                (optional).
            change_address: A string with address where ADA in excess of the transaction fee
                will go to (`src_address` by default).
            fee_buffer: A buffer for fee amount (optional).
            required_signers: An iterable of filepaths of the signing keys whose signatures
                are required (optional).
            required_signer_hashes: A list of hashes of the signing keys whose signatures
                are required (optional).
            withdrawals: A list (iterable) of `TxOuts`, specifying reward withdrawals (optional).
            script_withdrawals: An iterable of `ScriptWithdrawal`, specifying withdrawal script
                data (optional).
            deposit: A deposit amount needed by the transaction (optional).
            invalid_hereafter: A last block when the transaction is still valid (optional).
            invalid_before: A first block when the transaction is valid (optional).
            witness_override: An integer indicating real number of witnesses. Can be used to fix
                fee calculation (optional).
            script_valid: A bool indicating that the script is valid (True by default).
            calc_script_cost_file: A path for output of the Plutus script cost information
                (optional).
            join_txouts: A bool indicating whether to aggregate transaction outputs
                by payment address (True by default).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            List[dict]: A Plutus scripts cost data.
        """
        # pylint: disable=too-many-arguments,unused-argument
        # collect all arguments that will be passed to `build_tx`
        kwargs = locals()
        kwargs.pop("self", None)
        kwargs.pop("kwargs", None)
        # this would be a duplicate if already present
        kwargs.pop("calc_script_cost_file", None)

        destination_dir = Path(destination_dir).expanduser()
        out_file = destination_dir / f"{tx_name}_plutus.cost"

        self.build_tx(**kwargs, calc_script_cost_file=out_file)
        with open(out_file, encoding="utf-8") as fp_out:
            cost: List[dict] = json.load(fp_out)
        return cost

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
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        self.cli(
            [
                "governance",
                "create-update-proposal",
                *cli_args,
                "--out-file",
                str(out_file),
                "--epoch",
                str(epoch),
                *helpers._prepend_flag(
                    "--genesis-verification-key-file", self.genesis_keys.genesis_vkeys
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
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        self.cli(
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
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        self.cli(
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
        clusterlib_helpers._check_files_exist(out_file, clusterlib_obj=self)

        self.cli(
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
        epoch = epoch if epoch is not None else self.get_epoch()

        out_file = self.gen_update_proposal(
            cli_args=cli_args,
            epoch=epoch,
            tx_name=tx_name,
            destination_dir=destination_dir,
        )

        return self.send_tx(
            src_address=src_address,
            tx_name=f"{tx_name}_submit_proposal",
            tx_files=structs.TxFiles(
                proposal_files=[out_file],
                signing_key_files=[*self.genesis_keys.delegate_skeys, Path(src_skey_file)],
            ),
            destination_dir=destination_dir,
        )

    def send_funds(
        self,
        src_address: str,
        destinations: List[structs.TxOut],
        tx_name: str,
        tx_files: Optional[structs.TxFiles] = None,
        fee: Optional[int] = None,
        ttl: Optional[int] = None,
        deposit: Optional[int] = None,
        invalid_hereafter: Optional[int] = None,
        verify_tx: bool = True,
        destination_dir: FileType = ".",
    ) -> structs.TxRawOutput:
        """Send funds - convenience function for `send_tx`.

        Args:
            src_address: An address used for fee and inputs.
            destinations: A list (iterable) of `TxOuts`, specifying transaction outputs.
            tx_name: A name of the transaction.
            tx_files: A `structs.TxFiles` tuple containing files needed for the transaction
                (optional).
            fee: A fee amount (optional).
            ttl: A last block when the transaction is still valid
                (deprecated in favor of `invalid_hereafter`, optional).
            deposit: A deposit amount needed by the transaction (optional).
            invalid_hereafter: A last block when the transaction is still valid (optional).
            verify_tx: A bool indicating whether to verify the transaction made it to chain
                and resubmit the transaction if not (True by default).
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            structs.TxRawOutput: A tuple with transaction output details.
        """
        # pylint: disable=too-many-arguments
        return self.send_tx(
            src_address=src_address,
            tx_name=tx_name,
            txouts=destinations,
            tx_files=tx_files,
            fee=fee,
            deposit=deposit,
            invalid_hereafter=invalid_hereafter or ttl,
            destination_dir=destination_dir,
            verify_tx=verify_tx,
        )

    def wait_for_new_block(self, new_blocks: int = 1) -> int:
        """Wait for new block(s) to be created.

        Args:
            new_blocks: A number of new blocks to wait for (optional).

        Returns:
            int: A block number of last added block.
        """
        initial_tip = self.get_tip()
        initial_block = int(initial_tip["block"])
        initial_slot = int(initial_tip["slot"])

        if new_blocks < 1:
            return initial_block

        next_block_timeout = 300  # in slots
        max_tip_throttle = 5 * self.slot_length

        LOGGER.debug(f"Waiting for {new_blocks} new block(s) to be created.")
        LOGGER.debug(f"Initial block no: {initial_block}")

        this_slot = initial_slot
        this_block = initial_block
        timeout_slot = initial_slot + next_block_timeout
        expected_block = initial_block + new_blocks
        blocks_to_go = new_blocks
        # limit calls to `query tip`
        tip_throttle = 0

        while this_slot < timeout_slot:
            prev_block = this_block
            time.sleep((self.slot_length * blocks_to_go) + tip_throttle)

            this_tip = self.get_tip()
            this_slot = int(this_tip["slot"])
            this_block = int(this_tip["block"])

            if this_block >= expected_block:
                break
            if this_block > prev_block:
                # new block was created, reset timeout slot
                timeout_slot = this_slot + next_block_timeout

            blocks_to_go = expected_block - this_block
            tip_throttle = min(max_tip_throttle, tip_throttle + self.slot_length)
        else:
            waited_sec = (this_slot - initial_slot) * self.slot_length
            raise exceptions.CLIError(
                f"Timeout waiting for {waited_sec} sec for {new_blocks} block(s)."
            )

        LOGGER.debug(f"New block(s) were created; block number: {this_block}")
        return this_block

    def wait_for_slot(self, slot: int) -> int:
        """Wait for slot number.

        Args:
            slot: A slot number to wait for.

        Returns:
            int: A slot number of last block.
        """
        min_sleep = 1.5
        no_block_time = 0  # in slots
        next_block_timeout = 300  # in slots
        last_slot = -1
        printed = False
        for __ in range(100):
            this_slot = self.get_slot_no()

            slots_diff = slot - this_slot
            if slots_diff <= 0:
                return this_slot

            if this_slot == last_slot:
                if no_block_time >= next_block_timeout:
                    raise exceptions.CLIError(
                        f"Failed to wait for slot number {slot}, no new blocks are being created."
                    )
            else:
                no_block_time = 0

            _sleep_time = slots_diff * self.slot_length
            sleep_time = _sleep_time if _sleep_time > min_sleep else min_sleep

            if not printed and sleep_time > 15:
                LOGGER.info(f"Waiting for {sleep_time:.2f} sec for slot no {slot}.")
                printed = True

            last_slot = this_slot
            no_block_time += slots_diff
            time.sleep(sleep_time)

        raise exceptions.CLIError(f"Failed to wait for slot number {slot}.")

    def poll_new_epoch(self, exp_epoch: int, padding_seconds: int = 0) -> None:
        """Wait for new epoch(s) by polling current epoch every 3 sec.

        Can be used only for waiting up to 3000 sec + padding seconds.

        Args:
            exp_epoch: An epoch number to wait for.
            padding_seconds: A number of additional seconds to wait for (optional).
        """
        for check_no in range(1000):
            wakeup_epoch = self.get_epoch()
            if wakeup_epoch != exp_epoch:
                time.sleep(3)
                continue
            # we are in the expected epoch right from the beginning, we'll skip padding seconds
            if check_no == 0:
                break
            if padding_seconds:
                time.sleep(padding_seconds)
                break

    def wait_for_new_epoch(self, new_epochs: int = 1, padding_seconds: int = 0) -> int:
        """Wait for new epoch(s).

        Args:
            new_epochs: A number of new epochs to wait for (optional).
            padding_seconds: A number of additional seconds to wait for (optional).

        Returns:
            int: The current epoch.
        """
        start_epoch = self.get_epoch()

        if new_epochs < 1:
            return start_epoch

        exp_epoch = start_epoch + new_epochs
        LOGGER.debug(
            f"Current epoch: {start_epoch}; Waiting for the beginning of epoch: {exp_epoch}"
        )

        # calculate and wait for the expected slot
        boundary_slot = int((start_epoch + new_epochs) * self.epoch_length - self.slots_offset)
        padding_slots = int(padding_seconds / self.slot_length) if padding_seconds else 5
        exp_slot = boundary_slot + padding_slots
        self.wait_for_slot(slot=exp_slot)

        this_epoch = self.get_epoch()
        if this_epoch != exp_epoch:
            LOGGER.error(
                f"Waited for epoch number {exp_epoch} and current epoch is "
                f"number {this_epoch}, wrong `slots_offset` ({self.slots_offset})?"
            )
            # attempt to get the epoch boundary as precisely as possible failed, now just
            # query epoch number and wait
            self.poll_new_epoch(exp_epoch=exp_epoch, padding_seconds=padding_seconds)

        # Still not in the correct epoch? Something is wrong.
        this_epoch = self.get_epoch()
        if this_epoch != exp_epoch:
            raise exceptions.CLIError(
                f"Waited for epoch number {exp_epoch} and current epoch is number {this_epoch}."
            )

        LOGGER.debug(f"Expected epoch started; epoch number: {this_epoch}")
        return this_epoch

    def time_to_epoch_end(self, tip: Optional[dict] = None) -> float:
        """How many seconds to go to start of a new epoch."""
        tip = tip or self.get_tip()
        epoch = int(tip["epoch"])
        slot = int(tip["slot"])
        slots_to_go = (epoch + 1) * self.epoch_length - (slot + self.slots_offset - 1)
        return float(slots_to_go * self.slot_length)

    def time_from_epoch_start(self, tip: Optional[dict] = None) -> float:
        """How many seconds passed from start of the current epoch."""
        s_to_epoch_stop = self.time_to_epoch_end(tip=tip)
        return float(self.epoch_length_sec - s_to_epoch_stop)

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
            pool_data: A `structs.PoolData` tuple cointaining info about the stake pool.
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

        tx_raw_output = self.send_tx(
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
            f"Current epoch is: {self.get_epoch()}"
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

        tx_raw_output = self.send_tx(
            src_address=pool_owners[0].payment.address,
            tx_name=tx_name,
            tx_files=tx_files,
            destination_dir=destination_dir,
        )

        return pool_dereg_cert_file, tx_raw_output

    def create_stake_pool(
        self,
        pool_data: structs.PoolData,
        pool_owners: List[structs.PoolUser],
        tx_name: str,
        destination_dir: FileType = ".",
    ) -> structs.PoolCreationOutput:
        """Create and register a stake pool.

        Args:
            pool_data: A `structs.PoolData` tuple cointaining info about the stake pool.
            pool_owners: A list of `structs.PoolUser` structures containing pool user addresses
                and keys.
            tx_name: A name of the transaction.
            destination_dir: A path to directory for storing artifacts (optional).

        Returns:
            structs.PoolCreationOutput: A tuple containing pool creation output.
        """
        # create the KES key pair
        node_kes = self.gen_kes_key_pair(
            node_name=pool_data.pool_name,
            destination_dir=destination_dir,
        )
        LOGGER.debug(f"KES keys created - {node_kes.vkey_file}; {node_kes.skey_file}")

        # create the VRF key pair
        node_vrf = self.gen_vrf_key_pair(
            node_name=pool_data.pool_name,
            destination_dir=destination_dir,
        )
        LOGGER.debug(f"VRF keys created - {node_vrf.vkey_file}; {node_vrf.skey_file}")

        # create the cold key pair and node operational certificate counter
        node_cold = self.gen_cold_key_pair_and_counter(
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

    def withdraw_reward(
        self,
        stake_addr_record: structs.AddressRecord,
        dst_addr_record: structs.AddressRecord,
        tx_name: str,
        verify: bool = True,
        destination_dir: FileType = ".",
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
        src_init_balance = self.get_address_balance(dst_address)

        tx_files_withdrawal = structs.TxFiles(
            signing_key_files=[dst_addr_record.skey_file, stake_addr_record.skey_file],
        )

        tx_raw_withdrawal_output = self.send_tx(
            src_address=dst_address,
            tx_name=f"{tx_name}_reward_withdrawal",
            tx_files=tx_files_withdrawal,
            withdrawals=[structs.TxOut(address=stake_addr_record.address, amount=-1)],
            destination_dir=destination_dir,
        )

        if not verify:
            return tx_raw_withdrawal_output

        # check that reward is 0
        if self.get_stake_addr_info(stake_addr_record.address).reward_account_balance != 0:
            raise exceptions.CLIError("Not all rewards were transferred.")

        # check that rewards were transferred
        src_reward_balance = self.get_address_balance(dst_address)
        if (
            src_reward_balance
            != src_init_balance
            - tx_raw_withdrawal_output.fee
            + tx_raw_withdrawal_output.withdrawals[0].amount  # type: ignore
        ):
            raise exceptions.CLIError(f"Incorrect balance for destination address `{dst_address}`.")

        return tx_raw_withdrawal_output

    def __repr__(self) -> str:
        return f"<ClusterLib: protocol={self.protocol}, tx_era={self.tx_era}>"
