import enum
import typing as tp

DEFAULT_COIN: tp.Final[str] = "lovelace"
MAINNET_MAGIC: tp.Final[int] = 764824073

# offset of slots from Byron configuration vs current era configuration
SLOTS_OFFSETS: tp.Final[tp.Dict[int, int]] = {
    764824073: 85363200,  # mainnet
    1097911063: 30369600,  # testnet
    1: 1641600,  # preprod
}


# The SUBCOMMAND_MARK is used to mark the beginning of a subcommand. It is used to differentiate
# between options and subcommands. That is needed for CLI coverage recording.
# For example, the command `cardano-cli query tx-mempool --cardano-mode info`
# has the following arguments:
#  ["query", "tx-mempool", "--cardano-mode", SUBCOMMAND_MARK, "info"]
SUBCOMMAND_MARK: tp.Final[str] = "SUBCOMMAND"


class Protocols:
    CARDANO: tp.Final[str] = "cardano"
    SHELLEY: tp.Final[str] = "shelley"


class Eras(enum.Enum):
    BYRON: int = 1
    SHELLEY: int = 2
    ALLEGRA: int = 3
    MARY: int = 4
    ALONZO: int = 6
    BABBAGE: int = 8
    CONWAY: int = 9
    DEFAULT: int = BABBAGE
    LATEST: int = BABBAGE


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


class Votes(enum.Enum):
    YES: int = 1
    NO: int = 2
    ABSTAIN: int = 3
