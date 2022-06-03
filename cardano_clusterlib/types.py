from pathlib import Path
from typing import List
from typing import Set
from typing import Tuple
from typing import TYPE_CHECKING
from typing import Union

if TYPE_CHECKING:
    # pylint: disable=unused-import
    from cardano_clusterlib.clusterlib_klass import ClusterLib  # noqa: F401

FileType = Union[str, Path]
FileTypeList = Union[List[str], List[Path], Set[str], Set[Path]]
# TODO: needed until https://github.com/python/typing/issues/256 is fixed
UnpackableSequence = Union[list, tuple, set, frozenset]
# list of `FileType`s, empty list, or empty tuple
OptionalFiles = Union[FileTypeList, Tuple[()]]
