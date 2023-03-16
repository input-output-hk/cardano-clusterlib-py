DEFAULT_COIN = "lovelace"
MAINNET_MAGIC = 764824073

# offset of slots from Byron configuration vs current era configuration
SLOTS_OFFSETS = {
    764824073: 85363200,  # mainnet
    1097911063: 30369600,  # testnet
    1: 1641600,  # preprod
}


# The SUBCOMMAND_MARK is used to mark the beginning of a subcommand. It is used to differentiate
# between options and subcommands. That is needed for CLI coverage recording.
# For example, the command `cardano-cli query tx-mempool --cardano-mode info`
# has the following arguments:
#  ["query", "tx-mempool", "--cardano-mode", SUBCOMMAND_MARK, "info"]
SUBCOMMAND_MARK = "SUBCOMMAND"


class Protocols:
    CARDANO = "cardano"
    SHELLEY = "shelley"


class Eras:
    SHELLEY = "shelley"
    ALLEGRA = "allegra"
    MARY = "mary"
    ALONZO = "alonzo"


class MultiSigTypeArgs:
    ALL = "all"
    ANY = "any"
    AT_LEAST = "atLeast"


class MultiSlotTypeArgs:
    BEFORE = "before"
    AFTER = "after"


class ScriptTypes:
    SIMPLE_V1 = "simple_v1"
    SIMPLE_V2 = "simple_v2"
    PLUTUS_V1 = "plutus_v1"
    PLUTUS_V2 = "plutus_v2"
