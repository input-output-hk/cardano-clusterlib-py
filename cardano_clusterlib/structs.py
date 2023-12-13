import datetime
import pathlib as pl
import typing as tp

from cardano_clusterlib import consts
from cardano_clusterlib import types as itp


class CLIOut(tp.NamedTuple):
    stdout: bytes
    stderr: bytes


class KeyPair(tp.NamedTuple):
    vkey_file: pl.Path
    skey_file: pl.Path


class ColdKeyPair(tp.NamedTuple):
    vkey_file: pl.Path
    skey_file: pl.Path
    counter_file: pl.Path


class AddressRecord(tp.NamedTuple):
    address: str
    vkey_file: pl.Path
    skey_file: pl.Path


class StakeAddrInfo(tp.NamedTuple):
    address: str
    delegation: str
    reward_account_balance: int
    delegation_deposit: int
    vote_delegation: str

    def __bool__(self) -> bool:
        return bool(self.address)


class UTXOData(tp.NamedTuple):
    utxo_hash: str
    utxo_ix: int
    amount: int
    address: str
    coin: str = consts.DEFAULT_COIN
    decoded_coin: str = ""
    datum_hash: str = ""
    inline_datum_hash: str = ""
    inline_datum: tp.Optional[tp.Union[str, dict]] = None
    reference_script: tp.Optional[dict] = None


class TxOut(tp.NamedTuple):
    address: str
    amount: int
    coin: str = consts.DEFAULT_COIN
    datum_hash: str = ""
    datum_hash_file: itp.FileType = ""
    datum_hash_cbor_file: itp.FileType = ""
    datum_hash_value: str = ""
    datum_embed_file: itp.FileType = ""
    datum_embed_cbor_file: itp.FileType = ""
    datum_embed_value: str = ""
    inline_datum_file: itp.FileType = ""
    inline_datum_cbor_file: itp.FileType = ""
    inline_datum_value: str = ""
    reference_script_file: itp.FileType = ""


# list of `TxOut`s, empty list, or empty tuple
OptionalTxOuts = tp.Union[tp.List[TxOut], tp.Tuple[()]]
# list of `UTXOData`s, empty list, or empty tuple
OptionalUTXOData = tp.Union[tp.List[UTXOData], tp.Tuple[()]]  # pylint: disable=invalid-name


class ScriptTxIn(tp.NamedTuple):
    """Data structure for Tx inputs that are combined with scripts (simple or Plutus)."""

    txins: tp.List[UTXOData]
    script_file: itp.FileType = ""
    reference_txin: tp.Optional[UTXOData] = None
    reference_type: str = ""
    # values below needed only when working with Plutus
    collaterals: OptionalUTXOData = ()
    execution_units: tp.Optional[tp.Tuple[int, int]] = None
    datum_file: itp.FileType = ""
    datum_cbor_file: itp.FileType = ""
    datum_value: str = ""
    inline_datum_present: bool = False
    redeemer_file: itp.FileType = ""
    redeemer_cbor_file: itp.FileType = ""
    redeemer_value: str = ""


class ScriptWithdrawal(tp.NamedTuple):
    """Data structure for withdrawals that are combined with Plutus scripts."""

    txout: TxOut
    script_file: itp.FileType = ""
    reference_txin: tp.Optional[UTXOData] = None
    reference_type: str = ""
    collaterals: OptionalUTXOData = ()
    execution_units: tp.Optional[tp.Tuple[int, int]] = None
    redeemer_file: itp.FileType = ""
    redeemer_cbor_file: itp.FileType = ""
    redeemer_value: str = ""


class ComplexCert(tp.NamedTuple):
    """Data structure for certificates with optional data for Plutus scripts.

    If used for one certificate, it needs to be used for all the other certificates in a given
    transaction (instead of `TxFiles.certificate_files`). Otherwise, order of certificates
    cannot be guaranteed.
    """

    certificate_file: itp.FileType
    script_file: itp.FileType = ""
    reference_txin: tp.Optional[UTXOData] = None
    reference_type: str = ""
    collaterals: OptionalUTXOData = ()
    execution_units: tp.Optional[tp.Tuple[int, int]] = None
    redeemer_file: itp.FileType = ""
    redeemer_cbor_file: itp.FileType = ""
    redeemer_value: str = ""


class Mint(tp.NamedTuple):
    txouts: tp.List[TxOut]
    script_file: itp.FileType = ""
    reference_txin: tp.Optional[UTXOData] = None
    reference_type: str = ""
    policyid: str = ""
    # values below needed only when working with Plutus
    collaterals: OptionalUTXOData = ()
    execution_units: tp.Optional[tp.Tuple[int, int]] = None
    redeemer_file: itp.FileType = ""
    redeemer_cbor_file: itp.FileType = ""
    redeemer_value: str = ""


# list of `ScriptTxIn`s, empty list, or empty tuple
OptionalScriptTxIn = tp.Union[tp.List[ScriptTxIn], tp.Tuple[()]]
# list of `ComplexCert`s, empty list, or empty tuple
OptionalScriptCerts = tp.Union[tp.List[ComplexCert], tp.Tuple[()]]
# list of `ScriptWithdrawal`s, empty list, or empty tuple
OptionalScriptWithdrawals = tp.Union[tp.List[ScriptWithdrawal], tp.Tuple[()]]
# list of `Mint`s, empty list, or empty tuple
OptionalMint = tp.Union[tp.List[Mint], tp.Tuple[()]]


class TxFiles(tp.NamedTuple):
    certificate_files: itp.OptionalFiles = ()
    proposal_files: itp.OptionalFiles = ()
    metadata_json_files: itp.OptionalFiles = ()
    metadata_cbor_files: itp.OptionalFiles = ()
    signing_key_files: itp.OptionalFiles = ()
    auxiliary_script_files: itp.OptionalFiles = ()
    vote_files: itp.OptionalFiles = ()
    metadata_json_detailed_schema: bool = False


class PoolUser(tp.NamedTuple):
    payment: AddressRecord
    stake: AddressRecord


class PoolData(tp.NamedTuple):
    pool_name: str
    pool_pledge: int
    pool_cost: int
    pool_margin: float
    pool_metadata_url: str = ""
    pool_metadata_hash: str = ""
    pool_relay_dns: str = ""
    pool_relay_ipv4: str = ""
    pool_relay_port: int = 0


class TxRawOutput(tp.NamedTuple):
    txins: tp.List[UTXOData]  # UTXOs used as inputs
    txouts: tp.List[TxOut]  # Tx outputs
    txouts_count: int  # Final number of tx outputs after adding change address and joining outputs
    tx_files: TxFiles  # Files needed for transaction building (certificates, signing keys, etc.)
    out_file: pl.Path  # Output file path for the transaction body
    fee: int  # Tx fee
    build_args: tp.List[str]  # Arguments that were passed to `cardano-cli transaction build*`
    era: str = ""  # Era used for the transaction
    script_txins: OptionalScriptTxIn = ()  # Tx inputs that are combined with scripts
    script_withdrawals: OptionalScriptWithdrawals = ()  # Withdrawals that are combined with scripts
    complex_certs: OptionalScriptCerts = ()  # Certificates that are combined with scripts
    mint: OptionalMint = ()  # Minting data (Tx outputs, script, etc.)
    invalid_hereafter: tp.Optional[int] = None  # Validity interval upper bound
    invalid_before: tp.Optional[int] = None  # Validity interval lower bound
    withdrawals: OptionalTxOuts = ()  # All withdrawals (including those combined with scripts)
    change_address: str = ""  # Address for change
    return_collateral_txouts: OptionalTxOuts = ()  # Tx outputs for returning collateral
    total_collateral_amount: tp.Optional[int] = None  # Total collateral amount
    readonly_reference_txins: OptionalUTXOData = ()  # Tx inputs for plutus script context
    script_valid: bool = True  # Whether the plutus script is valid
    required_signers: itp.OptionalFiles = ()  # Signing keys required for the transaction
    # Hashes of signing keys that are required for the transaction
    required_signer_hashes: tp.Union[tp.List[str], tp.Tuple[()]] = ()
    combined_reference_txins: OptionalUTXOData = ()  # All reference tx inputs


class PoolCreationOutput(tp.NamedTuple):
    stake_pool_id: str
    vrf_key_pair: KeyPair
    cold_key_pair: ColdKeyPair
    pool_reg_cert_file: pl.Path
    pool_data: PoolData
    pool_owners: tp.List[PoolUser]
    tx_raw_output: TxRawOutput
    kes_key_pair: tp.Optional[KeyPair] = None


class GenesisKeys(tp.NamedTuple):
    genesis_utxo_vkey: pl.Path
    genesis_utxo_skey: pl.Path
    genesis_vkeys: tp.List[pl.Path]
    delegate_skeys: tp.List[pl.Path]


class PoolParamsTop(tp.NamedTuple):
    pool_params: dict
    future_pool_params: dict
    retiring: tp.Optional[int]


class AddressInfo(tp.NamedTuple):
    address: str
    era: str
    encoding: str
    type: str
    base16: str


class Value(tp.NamedTuple):
    value: int
    coin: str


class LeadershipSchedule(tp.NamedTuple):
    slot_no: int
    utc_time: datetime.datetime


class DataForBuild(tp.NamedTuple):
    txins: tp.List[UTXOData]
    txouts: tp.List[TxOut]
    withdrawals: OptionalTxOuts
    script_withdrawals: OptionalScriptWithdrawals


class CCMember(tp.NamedTuple):
    epoch: int
    cold_vkey: str = ""
    cold_vkey_file: itp.FileType = ""
    cold_vkey_hash: str = ""
    cold_skey: str = ""
    cold_skey_file: itp.FileType = ""
    cold_skey_hash: str = ""
    hot_vkey: str = ""
    hot_vkey_file: itp.FileType = ""
    hot_vkey_hash: str = ""
    hot_skey: str = ""
    hot_skey_file: itp.FileType = ""
    hot_skey_hash: str = ""


class VoteCC(tp.NamedTuple):
    action_txid: str
    action_ix: int
    vote: consts.Votes
    key_hash: str
    vote_file: pl.Path
    cc_hot_vkey: str = ""
    cc_hot_vkey_file: tp.Optional[itp.FileType] = None
    cc_hot_key_hash: str = ""
    anchor_url: str = ""
    anchor_data_hash: str = ""


class VoteDrep(tp.NamedTuple):
    action_txid: str
    action_ix: int
    vote: consts.Votes
    key_hash: str
    vote_file: pl.Path
    drep_vkey: str = ""
    drep_vkey_file: tp.Optional[itp.FileType] = None
    drep_key_hash: str = ""
    anchor_url: str = ""
    anchor_data_hash: str = ""


class VoteSPO(tp.NamedTuple):
    action_txid: str
    action_ix: int
    vote: consts.Votes
    key_hash: str
    vote_file: pl.Path
    stake_pool_vkey: str = ""
    cold_vkey_file: tp.Optional[itp.FileType] = None
    stake_pool_id: str = ""
    anchor_url: str = ""
    anchor_data_hash: str = ""
