"""Wrapper for cardano-cli for working with cardano cluster."""
import json
import logging
import subprocess
import time
from pathlib import Path
from typing import List
from typing import Optional

from cardano_clusterlib import address_group
from cardano_clusterlib import clusterlib_helpers
from cardano_clusterlib import consts
from cardano_clusterlib import coverage
from cardano_clusterlib import exceptions
from cardano_clusterlib import genesis_group
from cardano_clusterlib import governance_group
from cardano_clusterlib import helpers
from cardano_clusterlib import key_group
from cardano_clusterlib import node_group
from cardano_clusterlib import query_group
from cardano_clusterlib import stake_address_group
from cardano_clusterlib import stake_pool_group
from cardano_clusterlib import structs
from cardano_clusterlib import transaction_group
from cardano_clusterlib.types import FileType


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

    # pylint: disable=too-many-instance-attributes

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
        self.protocol = protocol

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

        # TODO: add temporary switch for CDDL format, until it is made default
        self.use_cddl = False

        self.overwrite_outfiles = True

        # groups of commands
        self._transaction_group: Optional[transaction_group.TransactionGroup] = None
        self._query_group: Optional[query_group.QueryGroup] = None
        self._address_group: Optional[address_group.AddressGroup] = None
        self._stake_address_group: Optional[stake_address_group.StakeAddressGroup] = None
        self._stake_pool_group: Optional[stake_pool_group.StakePoolGroup] = None
        self._node_group: Optional[node_group.NodeGroup] = None
        self._key_group: Optional[key_group.KeyGroup] = None
        self._genesis_group: Optional[genesis_group.GenesisGroup] = None
        self._governance_group: Optional[governance_group.GovernanceGroup] = None

        clusterlib_helpers._check_protocol(clusterlib_obj=self)

    @property
    def g_transaction(self) -> transaction_group.TransactionGroup:
        """Transaction group."""
        if not self._transaction_group:
            self._transaction_group = transaction_group.TransactionGroup(clusterlib_obj=self)
        return self._transaction_group

    @property
    def g_query(self) -> query_group.QueryGroup:
        """Query group."""
        if not self._query_group:
            self._query_group = query_group.QueryGroup(clusterlib_obj=self)
        return self._query_group

    @property
    def g_address(self) -> address_group.AddressGroup:
        """Address group."""
        if not self._address_group:
            self._address_group = address_group.AddressGroup(clusterlib_obj=self)
        return self._address_group

    @property
    def g_stake_address(self) -> stake_address_group.StakeAddressGroup:
        """Stake address group."""
        if not self._stake_address_group:
            self._stake_address_group = stake_address_group.StakeAddressGroup(clusterlib_obj=self)
        return self._stake_address_group

    @property
    def g_stake_pool(self) -> stake_pool_group.StakePoolGroup:
        """Stake pool group."""
        if not self._stake_pool_group:
            self._stake_pool_group = stake_pool_group.StakePoolGroup(clusterlib_obj=self)
        return self._stake_pool_group

    @property
    def g_node(self) -> node_group.NodeGroup:
        """Node group."""
        if not self._node_group:
            self._node_group = node_group.NodeGroup(clusterlib_obj=self)
        return self._node_group

    @property
    def g_key(self) -> key_group.KeyGroup:
        """Key group."""
        if not self._key_group:
            self._key_group = key_group.KeyGroup(clusterlib_obj=self)
        return self._key_group

    @property
    def g_genesis(self) -> genesis_group.GenesisGroup:
        """Genesis group."""
        if not self._genesis_group:
            self._genesis_group = genesis_group.GenesisGroup(clusterlib_obj=self)
        return self._genesis_group

    @property
    def g_governance(self) -> governance_group.GovernanceGroup:
        """Governance group."""
        if not self._governance_group:
            self._governance_group = governance_group.GovernanceGroup(clusterlib_obj=self)
        return self._governance_group

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
            retcode = None
            with subprocess.Popen(cli_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
                stdout, stderr = p.communicate()
                retcode = p.returncode

            if retcode == 0:
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

    def refresh_pparams_file(self) -> None:
        """Refresh protocol parameters file."""
        self.g_query.query_cli(["protocol-parameters", "--out-file", str(self.pparams_file)])

    def create_pparams_file(self) -> None:
        """Create protocol parameters file if it doesn't exist."""
        if self.pparams_file.exists():
            return
        self.refresh_pparams_file()

    def wait_for_new_block(self, new_blocks: int = 1) -> int:
        """Wait for new block(s) to be created.

        Args:
            new_blocks: A number of new blocks to wait for (optional).

        Returns:
            int: A block number of last added block.
        """
        initial_tip = self.g_query.get_tip()
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

            this_tip = self.g_query.get_tip()
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
            this_slot = self.g_query.get_slot_no()

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
            wakeup_epoch = self.g_query.get_epoch()
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
        start_epoch = self.g_query.get_epoch()

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

        this_epoch = self.g_query.get_epoch()
        if this_epoch != exp_epoch:
            LOGGER.error(
                f"Waited for epoch number {exp_epoch} and current epoch is "
                f"number {this_epoch}, wrong `slots_offset` ({self.slots_offset})?"
            )
            # attempt to get the epoch boundary as precisely as possible failed, now just
            # query epoch number and wait
            self.poll_new_epoch(exp_epoch=exp_epoch, padding_seconds=padding_seconds)

        # Still not in the correct epoch? Something is wrong.
        this_epoch = self.g_query.get_epoch()
        if this_epoch != exp_epoch:
            raise exceptions.CLIError(
                f"Waited for epoch number {exp_epoch} and current epoch is number {this_epoch}."
            )

        LOGGER.debug(f"Expected epoch started; epoch number: {this_epoch}")
        return this_epoch

    def time_to_epoch_end(self, tip: Optional[dict] = None) -> float:
        """How many seconds to go to start of a new epoch."""
        tip = tip or self.g_query.get_tip()
        epoch = int(tip["epoch"])
        slot = int(tip["slot"])
        slots_to_go = (epoch + 1) * self.epoch_length - (slot + self.slots_offset - 1)
        return float(slots_to_go * self.slot_length)

    def time_from_epoch_start(self, tip: Optional[dict] = None) -> float:
        """How many seconds passed from start of the current epoch."""
        s_to_epoch_stop = self.time_to_epoch_end(tip=tip)
        return float(self.epoch_length_sec - s_to_epoch_stop)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: protocol={self.protocol}, tx_era={self.tx_era}>"
