import dataclasses
import datetime
import pathlib as pl
import typing as tp

from cardano_clusterlib import consts
from cardano_clusterlib import types as itp


@dataclasses.dataclass(frozen=True)
class CLIOut:
    stdout: bytes
    stderr: bytes


@dataclasses.dataclass(frozen=True, order=True)
class KeyPair:
    vkey_file: pl.Path
    skey_file: pl.Path


@dataclasses.dataclass(frozen=True, order=True)
class ColdKeyPair:
    vkey_file: pl.Path
    skey_file: pl.Path
    counter_file: pl.Path


@dataclasses.dataclass(frozen=True, order=True)
class AddressRecord:
    address: str
    vkey_file: pl.Path
    skey_file: pl.Path


@dataclasses.dataclass(frozen=True, order=True)
class StakeAddrInfo:
    address: str
    delegation: str
    reward_account_balance: int
    delegation_deposit: int
    vote_delegation: str

    def __bool__(self) -> bool:
        return bool(self.address)


@dataclasses.dataclass(frozen=True, order=True)
class UTXOData:
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


@dataclasses.dataclass(frozen=True, order=True)
class TxOut:
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


@dataclasses.dataclass(frozen=True, order=True)
class ScriptTxIn:
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


@dataclasses.dataclass(frozen=True, order=True)
class ScriptWithdrawal:
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


@dataclasses.dataclass(frozen=True, order=True)
class ComplexCert:
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


@dataclasses.dataclass(frozen=True, order=True)
class Mint:
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


@dataclasses.dataclass(frozen=True, order=True)
class TxFiles:
    certificate_files: itp.OptionalFiles = ()
    proposal_files: itp.OptionalFiles = ()
    metadata_json_files: itp.OptionalFiles = ()
    metadata_cbor_files: itp.OptionalFiles = ()
    signing_key_files: itp.OptionalFiles = ()
    auxiliary_script_files: itp.OptionalFiles = ()
    vote_files: itp.OptionalFiles = ()
    metadata_json_detailed_schema: bool = False


@dataclasses.dataclass(frozen=True, order=True)
class PoolUser:
    payment: AddressRecord
    stake: AddressRecord


@dataclasses.dataclass(frozen=True, order=True)
class PoolData:
    pool_name: str
    pool_pledge: int
    pool_cost: int
    pool_margin: float
    pool_metadata_url: str = ""
    pool_metadata_hash: str = ""
    pool_relay_dns: str = ""
    pool_relay_ipv4: str = ""
    pool_relay_port: int = 0


@dataclasses.dataclass(frozen=True, order=True)
class TxRawOutput:
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


@dataclasses.dataclass(frozen=True, order=True)
class PoolCreationOutput:
    stake_pool_id: str
    vrf_key_pair: KeyPair
    cold_key_pair: ColdKeyPair
    pool_reg_cert_file: pl.Path
    pool_data: PoolData
    pool_owners: tp.List[PoolUser]
    tx_raw_output: TxRawOutput
    kes_key_pair: tp.Optional[KeyPair] = None


@dataclasses.dataclass(frozen=True, order=True)
class GenesisKeys:
    genesis_utxo_vkey: pl.Path
    genesis_utxo_skey: pl.Path
    genesis_vkeys: tp.List[pl.Path]
    delegate_skeys: tp.List[pl.Path]


@dataclasses.dataclass(frozen=True, order=True)
class PoolParamsTop:
    pool_params: dict
    future_pool_params: dict
    retiring: tp.Optional[int]


@dataclasses.dataclass(frozen=True, order=True)
class AddressInfo:
    address: str
    era: str
    encoding: str
    type: str
    base16: str


@dataclasses.dataclass(frozen=True, order=True)
class Value:
    value: int
    coin: str


@dataclasses.dataclass(frozen=True, order=True)
class LeadershipSchedule:
    slot_no: int
    utc_time: datetime.datetime


@dataclasses.dataclass(frozen=True, order=True)
class DataForBuild:
    txins: tp.List[UTXOData]
    txouts: tp.List[TxOut]
    withdrawals: OptionalTxOuts
    script_withdrawals: OptionalScriptWithdrawals


@dataclasses.dataclass(frozen=True, order=True)
class CCMember:
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


@dataclasses.dataclass(frozen=True, order=True)
class VoteCC:
    action_txid: str
    action_ix: int
    vote: consts.Votes
    vote_file: pl.Path
    cc_hot_vkey: str = ""
    cc_hot_vkey_file: tp.Optional[pl.Path] = None
    cc_hot_key_hash: str = ""
    anchor_url: str = ""
    anchor_data_hash: str = ""


@dataclasses.dataclass(frozen=True, order=True)
class VoteDrep:
    action_txid: str
    action_ix: int
    vote: consts.Votes
    vote_file: pl.Path
    drep_vkey: str = ""
    drep_vkey_file: tp.Optional[pl.Path] = None
    drep_key_hash: str = ""
    anchor_url: str = ""
    anchor_data_hash: str = ""


@dataclasses.dataclass(frozen=True, order=True)
class VoteSPO:
    action_txid: str
    action_ix: int
    vote: consts.Votes
    vote_file: pl.Path
    stake_pool_vkey: str = ""
    cold_vkey_file: tp.Optional[pl.Path] = None
    stake_pool_id: str = ""
    anchor_url: str = ""
    anchor_data_hash: str = ""


@dataclasses.dataclass(frozen=True, order=True)
class ActionConstitution:
    action_file: pl.Path
    deposit_amt: int
    anchor_url: str
    anchor_data_hash: str
    constitution_url: str
    constitution_hash: str
    deposit_return_stake_vkey: str = ""
    deposit_return_stake_vkey_file: tp.Optional[pl.Path] = None
    deposit_return_stake_key_hash: str = ""
    prev_action_txid: str = ""
    prev_action_ix: int = -1


@dataclasses.dataclass(frozen=True, order=True)
class ActionInfo:
    action_file: pl.Path
    deposit_amt: int
    anchor_url: str
    anchor_data_hash: str
    deposit_return_stake_vkey: str = ""
    deposit_return_stake_vkey_file: tp.Optional[pl.Path] = None
    deposit_return_stake_key_hash: str = ""


@dataclasses.dataclass(frozen=True, order=True)
class ActionNoConfidence:
    action_file: pl.Path
    deposit_amt: int
    anchor_url: str
    anchor_data_hash: str
    prev_action_txid: str
    prev_action_ix: int
    deposit_return_stake_vkey: str = ""
    deposit_return_stake_vkey_file: tp.Optional[pl.Path] = None
    deposit_return_stake_key_hash: str = ""


@dataclasses.dataclass(frozen=True, order=True)
class ActionUpdateCommittee:
    action_file: pl.Path
    deposit_amt: int
    anchor_url: str
    anchor_data_hash: str
    threshold: str
    add_cc_members: tp.List[CCMember] = dataclasses.field(default_factory=list)
    rem_cc_members: tp.List[CCMember] = dataclasses.field(default_factory=list)
    prev_action_txid: str = ""
    prev_action_ix: int = -1
    deposit_return_stake_vkey: str = ""
    deposit_return_stake_vkey_file: tp.Optional[pl.Path] = None
    deposit_return_stake_key_hash: str = ""


@dataclasses.dataclass(frozen=True, order=True)
class ActionPParamsUpdate:
    action_file: pl.Path
    deposit_amt: int
    anchor_url: str
    anchor_data_hash: str
    cli_args: itp.UnpackableSequence
    prev_action_txid: str = ""
    prev_action_ix: int = -1
    deposit_return_stake_vkey: str = ""
    deposit_return_stake_vkey_file: tp.Optional[pl.Path] = None
    deposit_return_stake_key_hash: str = ""


@dataclasses.dataclass(frozen=True, order=True)
class ActionTreasuryWithdrawal:
    action_file: pl.Path
    transfer_amt: int
    deposit_amt: int
    anchor_url: str
    anchor_data_hash: str
    funds_receiving_stake_vkey: str = ""
    funds_receiving_stake_vkey_file: tp.Optional[pl.Path] = None
    funds_receiving_stake_key_hash: str = ""
    deposit_return_stake_vkey: str = ""
    deposit_return_stake_vkey_file: tp.Optional[pl.Path] = None
    deposit_return_stake_key_hash: str = ""


@dataclasses.dataclass(frozen=True, order=True)
class ActionHardfork:
    action_file: pl.Path
    deposit_amt: int
    anchor_url: str
    anchor_data_hash: str
    protocol_major_version: int
    protocol_minor_version: int
    prev_action_txid: str = ""
    prev_action_ix: int = -1
    deposit_return_stake_vkey: str = ""
    deposit_return_stake_vkey_file: tp.Optional[pl.Path] = None
    deposit_return_stake_key_hash: str = ""
