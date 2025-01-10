import enum
import typing as tp

DEFAULT_COIN: tp.Final[str] = "lovelace"
MAINNET_MAGIC: tp.Final[int] = 764824073
CONFIRM_BLOCKS_NUM: tp.Final[int] = 2

# The SUBCOMMAND_MARK is used to mark the beginning of a subcommand. It is used to differentiate
# between options and subcommands. That is needed for CLI coverage recording.
# For example, the command `cardano-cli query tx-mempool --cardano-mode info`
# has the following arguments:
#  ["query", "tx-mempool", "--cardano-mode", SUBCOMMAND_MARK, "info"]
SUBCOMMAND_MARK: tp.Final[str] = "SUBCOMMAND"


class CommandEras:
    SHELLEY: tp.Final[str] = "shelley"
    ALLEGRA: tp.Final[str] = "allegra"
    MARY: tp.Final[str] = "mary"
    ALONZO: tp.Final[str] = "alonzo"
    BABBAGE: tp.Final[str] = "babbage"
    CONWAY: tp.Final[str] = "conway"
    LATEST: tp.Final[str] = "latest"


class Eras(enum.Enum):
    BYRON = 1
    SHELLEY = 2
    ALLEGRA = 3
    MARY = 4
    ALONZO = 6
    BABBAGE = 8
    CONWAY = 9
    DEFAULT = CONWAY
    LATEST = CONWAY  # noqa: PIE796


class MultiSigTypeArgs:
    ALL: tp.Final[str] = "all"
    ANY: tp.Final[str] = "any"
    AT_LEAST: tp.Final[str] = "atLeast"


class MultiSlotTypeArgs:
    BEFORE: tp.Final[str] = "before"
    AFTER: tp.Final[str] = "after"


class ScriptTypes:
    SIMPLE_V1: tp.Final[str] = "simple_v1"
    SIMPLE_V2: tp.Final[str] = "simple_v2"
    PLUTUS_V1: tp.Final[str] = "plutus_v1"
    PLUTUS_V2: tp.Final[str] = "plutus_v2"
    PLUTUS_V3: tp.Final[str] = "plutus_v3"


class Votes(enum.Enum):
    YES = 1
    NO = 2
    ABSTAIN = 3
