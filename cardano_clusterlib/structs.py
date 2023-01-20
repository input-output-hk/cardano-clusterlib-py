import datetime
from pathlib import Path
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import Tuple
from typing import Union

from cardano_clusterlib import consts
from cardano_clusterlib.types import FileType
from cardano_clusterlib.types import OptionalFiles


class CLIOut(NamedTuple):
    stdout: bytes
    stderr: bytes


class KeyPair(NamedTuple):
    vkey_file: Path
    skey_file: Path


class ColdKeyPair(NamedTuple):
    vkey_file: Path
    skey_file: Path
    counter_file: Path


class AddressRecord(NamedTuple):
    address: str
    vkey_file: Path
    skey_file: Path


class StakeAddrInfo(NamedTuple):
    address: str
    delegation: str
    reward_account_balance: int

    def __bool__(self) -> bool:
        return bool(self.address)


class UTXOData(NamedTuple):
    utxo_hash: str
    utxo_ix: int
    amount: int
    address: str
    coin: str = consts.DEFAULT_COIN
    decoded_coin: str = ""
    datum_hash: str = ""
    inline_datum_hash: str = ""
    inline_datum: Optional[Union[str, dict]] = None
    reference_script: Optional[dict] = None


class TxOut(NamedTuple):
    address: str
    amount: int
    coin: str = consts.DEFAULT_COIN
    datum_hash: str = ""
    datum_hash_file: FileType = ""
    datum_hash_cbor_file: FileType = ""
    datum_hash_value: str = ""
    datum_embed_file: FileType = ""
    datum_embed_cbor_file: FileType = ""
    datum_embed_value: str = ""
    inline_datum_file: FileType = ""
    inline_datum_cbor_file: FileType = ""
    inline_datum_value: str = ""
    reference_script_file: FileType = ""


# list of `TxOut`s, empty list, or empty tuple
OptionalTxOuts = Union[List[TxOut], Tuple[()]]
# list of `UTXOData`s, empty list, or empty tuple
OptionalUTXOData = Union[List[UTXOData], Tuple[()]]


class ScriptTxIn(NamedTuple):
    """Data structure for Tx inputs that are combined with scripts (simple or Plutus)."""

    txins: List[UTXOData]
    script_file: FileType = ""
    reference_txin: Optional[UTXOData] = None
    reference_type: str = ""
    # values below needed only when working with Plutus
    collaterals: OptionalUTXOData = ()
    execution_units: Optional[Tuple[int, int]] = None
    datum_file: FileType = ""
    datum_cbor_file: FileType = ""
    datum_value: str = ""
    inline_datum_present: bool = False
    redeemer_file: FileType = ""
    redeemer_cbor_file: FileType = ""
    redeemer_value: str = ""


class ScriptWithdrawal(NamedTuple):
    """Data structure for withdrawals that are combined with Plutus scripts."""

    txout: TxOut
    script_file: FileType = ""
    reference_txin: Optional[UTXOData] = None
    reference_type: str = ""
    collaterals: OptionalUTXOData = ()
    execution_units: Optional[Tuple[int, int]] = None
    redeemer_file: FileType = ""
    redeemer_cbor_file: FileType = ""
    redeemer_value: str = ""


class ComplexCert(NamedTuple):
    """Data structure for certificates with optional data for Plutus scripts.

    If used for one certificate, it needs to be used for all the other certificates in a given
    transaction (instead of `TxFiles.certificate_files`). Otherwise, order of certificates
    cannot be guaranteed.
    """

    certificate_file: FileType
    script_file: FileType = ""
    reference_txin: Optional[UTXOData] = None
    reference_type: str = ""
    collaterals: OptionalUTXOData = ()
    execution_units: Optional[Tuple[int, int]] = None
    redeemer_file: FileType = ""
    redeemer_cbor_file: FileType = ""
    redeemer_value: str = ""


class Mint(NamedTuple):
    txouts: List[TxOut]
    script_file: FileType = ""
    reference_txin: Optional[UTXOData] = None
    reference_type: str = ""
    policyid: str = ""
    # values below needed only when working with Plutus
    collaterals: OptionalUTXOData = ()
    execution_units: Optional[Tuple[int, int]] = None
    redeemer_file: FileType = ""
    redeemer_cbor_file: FileType = ""
    redeemer_value: str = ""


# list of `ScriptTxIn`s, empty list, or empty tuple
OptionalScriptTxIn = Union[List[ScriptTxIn], Tuple[()]]
# list of `ComplexCert`s, empty list, or empty tuple
OptionalScriptCerts = Union[List[ComplexCert], Tuple[()]]
# list of `ScriptWithdrawal`s, empty list, or empty tuple
OptionalScriptWithdrawals = Union[List[ScriptWithdrawal], Tuple[()]]
# list of `Mint`s, empty list, or empty tuple
OptionalMint = Union[List[Mint], Tuple[()]]


class TxFiles(NamedTuple):
    certificate_files: OptionalFiles = ()
    proposal_files: OptionalFiles = ()
    metadata_json_files: OptionalFiles = ()
    metadata_cbor_files: OptionalFiles = ()
    signing_key_files: OptionalFiles = ()
    auxiliary_script_files: OptionalFiles = ()


class PoolUser(NamedTuple):
    payment: AddressRecord
    stake: AddressRecord


class PoolData(NamedTuple):
    pool_name: str
    pool_pledge: int
    pool_cost: int
    pool_margin: float
    pool_metadata_url: str = ""
    pool_metadata_hash: str = ""
    pool_relay_dns: str = ""
    pool_relay_ipv4: str = ""
    pool_relay_port: int = 0


class TxRawOutput(NamedTuple):
    txins: List[UTXOData]
    txouts: List[TxOut]
    txouts_count: int
    tx_files: TxFiles
    out_file: Path
    fee: int
    build_args: List[str]
    era: str = ""
    script_txins: OptionalScriptTxIn = ()
    script_withdrawals: OptionalScriptWithdrawals = ()
    complex_certs: OptionalScriptCerts = ()
    mint: OptionalMint = ()
    invalid_hereafter: Optional[int] = None
    invalid_before: Optional[int] = None
    withdrawals: OptionalTxOuts = ()
    change_address: str = ""
    return_collateral_txouts: OptionalTxOuts = ()
    total_collateral_amount: Optional[int] = None
    readonly_reference_txins: OptionalUTXOData = ()
    script_valid: bool = True


class PoolCreationOutput(NamedTuple):
    stake_pool_id: str
    vrf_key_pair: KeyPair
    cold_key_pair: ColdKeyPair
    pool_reg_cert_file: Path
    pool_data: PoolData
    pool_owners: List[PoolUser]
    tx_raw_output: TxRawOutput
    kes_key_pair: Optional[KeyPair] = None


class GenesisKeys(NamedTuple):
    genesis_utxo_vkey: Path
    genesis_utxo_skey: Path
    genesis_vkeys: List[Path]
    delegate_skeys: List[Path]


class PoolParamsTop(NamedTuple):
    pool_params: dict
    future_pool_params: dict
    retiring: Optional[int]


class AddressInfo(NamedTuple):
    address: str
    era: str
    encoding: str
    type: str
    base16: str


class Value(NamedTuple):
    value: int
    coin: str


class LeadershipSchedule(NamedTuple):
    slot_no: int
    utc_time: datetime.datetime


class DataForBuild(NamedTuple):
    txins: List[UTXOData]
    txouts: List[TxOut]
    withdrawals: OptionalTxOuts
    script_withdrawals: OptionalScriptWithdrawals
