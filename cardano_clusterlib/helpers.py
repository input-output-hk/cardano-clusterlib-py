import itertools
import pathlib as pl
import random
import string
import typing as tp

from cardano_clusterlib import exceptions
from cardano_clusterlib import types as itp


def get_rand_str(length: int = 8) -> str:
    """Return random ASCII lowercase string."""
    if length < 1:
        return ""
    return "".join(random.choice(string.ascii_lowercase) for i in range(length))


def read_address_from_file(addr_file: itp.FileType) -> str:
    """Read address stored in file."""
    with open(pl.Path(addr_file).expanduser(), encoding="utf-8") as in_file:
        return in_file.read().strip()


def _prepend_flag(flag: str, contents: itp.UnpackableSequence) -> tp.List[str]:
    """Prepend flag to every item of the sequence.

    Args:
        flag: A flag to prepend to every item of the `contents`.
        contents: A list (iterable) of content to be prepended.

    Returns:
        List[str]: A list of flag followed by content, see below.

    >>> ClusterLib._prepend_flag(None, "--foo", [1, 2, 3])
    ['--foo', '1', '--foo', '2', '--foo', '3']
    """
    return list(itertools.chain.from_iterable([flag, str(x)] for x in contents))


def _check_outfiles(*out_files: itp.FileType) -> None:
    """Check that the expected output files were created.

    Args:
        *out_files: Variable length list of expected output files.
    """
    for out_file in out_files:
        out_file_p = pl.Path(out_file).expanduser()
        if not out_file_p.exists():
            msg = f"The expected file `{out_file}` doesn't exist."
            raise exceptions.CLIError(msg)


def _maybe_path(file: tp.Optional[itp.FileType]) -> tp.Optional[pl.Path]:
    """Return `Path` if `file` is thruthy."""
    return pl.Path(file) if file else None
