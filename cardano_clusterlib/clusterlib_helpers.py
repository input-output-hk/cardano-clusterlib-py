"""Helper functions for `ClusterLib`."""

import dataclasses
import datetime
import json
import logging
import pathlib as pl
import re
import time
import typing as tp

from cardano_clusterlib import exceptions
from cardano_clusterlib import types as itp

LOGGER = logging.getLogger(__name__)

SPECIAL_ARG_CHARS_RE = re.compile("[^A-Za-z0-9/._-]")


@dataclasses.dataclass(frozen=True, order=True)
class EpochInfo:
    epoch: int
    first_slot: int
    last_slot: int


def _find_genesis_json(clusterlib_obj: "itp.ClusterLib") -> pl.Path:
    """Find Shelley genesis JSON file in state dir."""
    default = clusterlib_obj.state_dir / "shelley" / "genesis.json"
    if default.exists():
        return default

    potential = [
        *clusterlib_obj.state_dir.glob("*shelley*genesis.json"),
        *clusterlib_obj.state_dir.glob("*genesis*shelley.json"),
    ]
    if not potential:
        msg = f"Shelley genesis JSON file not found in `{clusterlib_obj.state_dir}`."
        raise exceptions.CLIError(msg)

    genesis_json = potential[0]
    LOGGER.debug(f"Using shelley genesis JSON file `{genesis_json}")
    return genesis_json


def _find_conway_genesis_json(clusterlib_obj: "itp.ClusterLib") -> pl.Path:
    """Find Conway genesis JSON file in state dir."""
    default = clusterlib_obj.state_dir / "shelley" / "genesis.conway.json"
    if default.exists():
        return default

    potential = [
        *clusterlib_obj.state_dir.glob("*conway*genesis.json"),
        *clusterlib_obj.state_dir.glob("*genesis*conway.json"),
    ]
    if not potential:
        msg = f"Conway genesis JSON file not found in `{clusterlib_obj.state_dir}`."
        raise exceptions.CLIError(msg)

    genesis_json = potential[0]
    LOGGER.debug(f"Using Conway genesis JSON file `{genesis_json}")
    return genesis_json


def _check_protocol(clusterlib_obj: "itp.ClusterLib") -> None:
    """Check that the cluster is running with the expected protocol."""
    try:
        clusterlib_obj.create_pparams_file()
    except exceptions.CLIError as exc:
        if "SingleEraInfo" not in str(exc):
            raise
        msg = f"The cluster is running with protocol different from '{clusterlib_obj.protocol}'."
        raise exceptions.CLIError(msg) from exc


def _check_files_exist(*out_files: itp.FileType, clusterlib_obj: "itp.ClusterLib") -> None:
    """Check that the output files don't already exist.

    Args:
        *out_files: Variable length list of expected output files.
        clusterlib_obj: An instance of `ClusterLib`.
    """
    if clusterlib_obj.overwrite_outfiles:
        return

    for out_file in out_files:
        out_file_p = pl.Path(out_file).expanduser()
        if out_file_p.exists():
            msg = f"The expected file `{out_file}` already exist."
            raise exceptions.CLIError(msg)


def _format_cli_args(cli_args: tp.List[str]) -> str:
    """Format CLI arguments for logging.

    Quote arguments with spaces and other "special" characters in them.

    Args:
        cli_args: List of CLI arguments.
    """
    processed_args = []
    for arg in cli_args:
        arg_p = f'"{arg}"' if SPECIAL_ARG_CHARS_RE.search(arg) else arg
        processed_args.append(arg_p)
    return " ".join(processed_args)


def _write_cli_log(clusterlib_obj: "itp.ClusterLib", command: str) -> None:
    if not clusterlib_obj._cli_log:
        return

    with open(clusterlib_obj._cli_log, "a", encoding="utf-8") as logfile:
        logfile.write(f"{datetime.datetime.now(tz=datetime.timezone.utc)}: {command}\n")


def _get_kes_period_info(kes_info: str) -> tp.Dict[str, tp.Any]:
    """Process the output of the `kes-period-info` command.

    Args:
        kes_info: The output of the `kes-period-info` command.
    """
    messages_str = kes_info.split("{")[0]
    messages_list = []

    valid_counters = False
    valid_kes_period = False

    if messages_str:
        message_entry: list = []

        for line in messages_str.split("\n"):
            line_s = line.strip()
            if not line_s:
                continue
            if not message_entry or line_s[0].isalpha():
                message_entry.append(line_s)
            else:
                messages_list.append(" ".join(message_entry))
                message_entry = [line_s]

        messages_list.append(" ".join(message_entry))

        for out_message in messages_list:
            if (
                "counter agrees with" in out_message
                or "counter ahead of the node protocol state counter by 1" in out_message
            ):
                valid_counters = True
            elif "correct KES period interval" in out_message:
                valid_kes_period = True

    # get output metrics
    metrics_str = kes_info.split("{")[-1]
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


def get_epoch_for_slot(cluster_obj: "itp.ClusterLib", slot_no: int) -> EpochInfo:
    """Given slot number, return corresponding epoch number and first and last slot of the epoch."""
    genesis_byron = cluster_obj.state_dir / "byron" / "genesis.json"
    if not genesis_byron.exists():
        msg = f"File '{genesis_byron}' does not exist."
        raise AssertionError(msg)

    with open(genesis_byron, encoding="utf-8") as in_json:
        byron_dict = json.load(in_json)

    byron_k = int(byron_dict["protocolConsts"]["k"])
    slots_in_byron_epoch = byron_k * 10
    slots_per_epoch_diff = cluster_obj.epoch_length - slots_in_byron_epoch
    num_byron_epochs = cluster_obj.slots_offset // slots_per_epoch_diff
    slots_in_byron = num_byron_epochs * slots_in_byron_epoch

    # slot is in Byron era
    if slot_no < slots_in_byron:
        epoch_no = slot_no // slots_in_byron_epoch
        first_slot_in_epoch = epoch_no * slots_in_byron_epoch
        last_slot_in_epoch = first_slot_in_epoch + slots_in_byron_epoch - 1
    # slot is in Shelley-based era
    else:
        slot_no_shelley = slot_no + cluster_obj.slots_offset
        epoch_no = slot_no_shelley // cluster_obj.epoch_length
        first_slot_in_epoch = epoch_no * cluster_obj.epoch_length - cluster_obj.slots_offset
        last_slot_in_epoch = first_slot_in_epoch + cluster_obj.epoch_length - 1

    return EpochInfo(epoch=epoch_no, first_slot=first_slot_in_epoch, last_slot=last_slot_in_epoch)


def wait_for_block(
    clusterlib_obj: "itp.ClusterLib", tip: tp.Dict[str, tp.Any], block_no: int
) -> int:
    """Wait for block number.

    Args:
        clusterlib_obj: An instance of `ClusterLib`.
        tip: Current tip - last block successfully applied to the ledger.
        block_no: A block number to wait for.

    Returns:
        int: A block number of last added block.
    """
    initial_block = int(tip["block"])
    initial_slot = int(tip["slot"])

    if initial_block >= block_no:
        return initial_block

    next_block_timeout = 300  # in slots
    max_tip_throttle = 5 * clusterlib_obj.slot_length

    new_blocks = block_no - initial_block

    LOGGER.debug(f"Waiting for {new_blocks} new block(s) to be created.")
    LOGGER.debug(f"Initial block no: {initial_block}")

    this_slot = initial_slot
    this_block = initial_block
    timeout_slot = initial_slot + next_block_timeout
    blocks_to_go = new_blocks
    # limit calls to `query tip`
    tip_throttle = 0

    while this_slot < timeout_slot:
        prev_block = this_block
        time.sleep((clusterlib_obj.slot_length * blocks_to_go) + tip_throttle)

        this_tip = clusterlib_obj.g_query.get_tip()
        this_slot = int(this_tip["slot"])
        this_block = int(this_tip["block"])

        if this_block >= block_no:
            break
        if this_block > prev_block:
            # new block was created, reset timeout slot
            timeout_slot = this_slot + next_block_timeout

        blocks_to_go = block_no - this_block
        tip_throttle = min(max_tip_throttle, tip_throttle + clusterlib_obj.slot_length)
    else:
        waited_sec = (this_slot - initial_slot) * clusterlib_obj.slot_length
        msg = f"Timeout waiting for {waited_sec} sec for {new_blocks} block(s)."
        raise exceptions.CLIError(msg)

    LOGGER.debug(f"New block(s) were created; block number: {this_block}")
    return this_block
