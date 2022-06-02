DEFAULT_COIN = "lovelace"
MAINNET_MAGIC = 764824073

# offset of slots from Byron configuration vs current era configuration
SLOTS_OFFSETS = {
    764824073: 85363200,  # mainnet
    1097911063: 30369600,  # testnet
}


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
