import itertools
import random
import string
from pathlib import Path
from typing import List

from cardano_clusterlib import exceptions
from cardano_clusterlib import types


def get_rand_str(length: int = 8) -> str:
    """Return random ASCII lowercase string."""
    if length < 1:
        return ""
    return "".join(random.choice(string.ascii_lowercase) for i in range(length))


def read_address_from_file(addr_file: types.FileType) -> str:
    """Read address stored in file."""
    with open(Path(addr_file).expanduser(), encoding="utf-8") as in_file:
        return in_file.read().strip()


def _prepend_flag(flag: str, contents: types.UnpackableSequence) -> List[str]:
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


def _check_outfiles(*out_files: types.FileType) -> None:
    """Check that the expected output files were created.

    Args:
        *out_files: Variable length list of expected output files.
    """
    for out_file in out_files:
        out_file = Path(out_file).expanduser()
        if not out_file.exists():
            raise exceptions.CLIError(f"The expected file `{out_file}` doesn't exist.")
