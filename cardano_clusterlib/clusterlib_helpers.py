"""Helper functions for `ClusterLib`."""
import datetime
import json
import logging
from pathlib import Path
from typing import Any
from typing import Dict

from cardano_clusterlib import exceptions
from cardano_clusterlib import types

LOGGER = logging.getLogger(__name__)


def _find_genesis_json(clusterlib_obj: "types.ClusterLib") -> Path:
    """Find shelley genesis JSON file in state dir."""
    default = clusterlib_obj.state_dir / "shelley" / "genesis.json"
    if default.exists():
        return default

    potential = [
        *clusterlib_obj.state_dir.glob("*shelley*genesis.json"),
        *clusterlib_obj.state_dir.glob("*genesis*shelley.json"),
    ]
    if not potential:
        raise exceptions.CLIError(
            f"Shelley genesis JSON file not found in `{clusterlib_obj.state_dir}`."
        )

    genesis_json = potential[0]
    LOGGER.debug(f"Using shelley genesis JSON file `{genesis_json}")
    return genesis_json


def _check_protocol(clusterlib_obj: "types.ClusterLib") -> None:
    """Check that the cluster is running with the expected protocol."""
    try:
        clusterlib_obj.create_pparams_file()
    except exceptions.CLIError as exc:
        if "SingleEraInfo" not in str(exc):
            raise
        raise exceptions.CLIError(
            f"The cluster is running with protocol different from '{clusterlib_obj.protocol}'."
        ) from exc


def _check_files_exist(*out_files: types.FileType, clusterlib_obj: "types.ClusterLib") -> None:
    """Check that the output files don't already exist.

    Args:
        *out_files: Variable length list of expected output files.
        clusterlib_obj: An instance of `ClusterLib`.
    """
    if clusterlib_obj.overwrite_outfiles:
        return

    for out_file in out_files:
        out_file = Path(out_file).expanduser()
        if out_file.exists():
            raise exceptions.CLIError(f"The expected file `{out_file}` already exist.")


def _write_cli_log(clusterlib_obj: "types.ClusterLib", command: str) -> None:
    if not clusterlib_obj._cli_log:
        return

    with open(clusterlib_obj._cli_log, "a", encoding="utf-8") as logfile:
        logfile.write(f"{datetime.datetime.now()}: {command}\n")


def _get_kes_period_info(kes_info: str) -> Dict[str, Any]:
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
