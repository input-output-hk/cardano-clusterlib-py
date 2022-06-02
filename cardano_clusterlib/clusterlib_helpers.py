"""Helper functions for `CLusterLib`."""
import datetime
import logging
from pathlib import Path

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
