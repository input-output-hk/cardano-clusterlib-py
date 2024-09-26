import enum
import typing as tp

DEFAULT_COIN: tp.Final[str] = "lovelace"
MAINNET_MAGIC: tp.Final[int] = 764824073

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
    BYRON: int = 1
    SHELLEY: int = 2
    ALLEGRA: int = 3
    MARY: int = 4
    ALONZO: int = 6
    BABBAGE: int = 8
    CONWAY: int = 9
    DEFAULT: int = CONWAY
    LATEST: int = CONWAY


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
    YES: int = 1
    NO: int = 2
    ABSTAIN: int = 3
