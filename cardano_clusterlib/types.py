import pathlib as pl
import typing as tp

if tp.TYPE_CHECKING:
    # pylint: disable=unused-import
    from cardano_clusterlib.clusterlib_klass import ClusterLib  # noqa: F401

FileType = tp.Union[str, pl.Path]
FileTypeList = tp.Union[tp.List[FileType], tp.List[str], tp.List[pl.Path]]
# list of `FileType`s, empty list, or empty tuple
OptionalFiles = tp.Union[FileTypeList, tp.Tuple[()]]
# TODO: needed until https://github.com/python/typing/issues/256 is fixed
UnpackableSequence = tp.Union[list, tuple, set, frozenset]
