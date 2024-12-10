import pathlib as pl
import typing as tp

if tp.TYPE_CHECKING:
    # pylint: disable=unused-import
    from cardano_clusterlib.clusterlib_klass import ClusterLib  # noqa: F401

FileType = str | pl.Path
FileTypeList = list[FileType] | list[str] | list[pl.Path]
# List of `FileType`s, empty list, or empty tuple
OptionalFiles = FileTypeList | tuple[()]
# TODO: needed until https://github.com/python/typing/issues/256 is fixed
UnpackableSequence = list | tuple | set | frozenset
