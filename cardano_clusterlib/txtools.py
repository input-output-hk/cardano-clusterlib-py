"""Tools used by `ClusterLib` for constructing transactions."""
import base64
import contextlib
import functools
import itertools
import logging
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Union

from cardano_clusterlib import consts
from cardano_clusterlib import exceptions
from cardano_clusterlib import helpers
from cardano_clusterlib import structs
from cardano_clusterlib import types  # pylint: disable=unused-import

LOGGER = logging.getLogger(__name__)


def _organize_tx_ins_outs_by_coin(
    tx_list: Union[List[structs.UTXOData], List[structs.TxOut], Tuple[()]]
) -> Dict[str, list]:
    """Organize transaction inputs or outputs by coin type."""
    db: Dict[str, list] = {}
    for rec in tx_list:
        if rec.coin not in db:
            db[rec.coin] = []
        db[rec.coin].append(rec)
    return db


def _organize_utxos_by_id(tx_list: List[structs.UTXOData]) -> Dict[str, List[structs.UTXOData]]:
    """Organize UTxOs by ID (hash#ix)."""
    db: Dict[str, List[structs.UTXOData]] = {}
    for rec in tx_list:
        utxo_id = f"{rec.utxo_hash}#{rec.utxo_ix}"
        if utxo_id not in db:
            db[utxo_id] = []
        db[utxo_id].append(rec)
    return db


def _get_usable_utxos(
    address_utxos: List[structs.UTXOData], coins: Set[str]
) -> List[structs.UTXOData]:
    """Get all UTxOs with no datum that contain any of the required coins (`coins`)."""
    txins_by_id = _organize_utxos_by_id(address_utxos)

    txins = []
    seen_ids = set()
    matching_with_datum = False
    for rec in address_utxos:
        utxo_id = f"{rec.utxo_hash}#{rec.utxo_ix}"
        if rec.coin in coins and utxo_id not in seen_ids:
            # don't select UTxOs with datum
            if rec.datum_hash or rec.inline_datum_hash:
                matching_with_datum = True
                continue
            seen_ids.add(utxo_id)
            txins.extend(txins_by_id[utxo_id])

    if not txins and matching_with_datum:
        raise exceptions.CLIError("The only matching UTxOs have datum.")

    return txins


def _collect_utxos_amount(
    utxos: List[structs.UTXOData], amount: int, min_change_value: int
) -> List[structs.UTXOData]:
    """Collect UTxOs so their total combined amount >= `amount`."""
    collected_utxos: List[structs.UTXOData] = []
    collected_amount = 0
    # `_min_change_value` applies only to ADA
    amount_plus_change = (
        amount + min_change_value if utxos and utxos[0].coin == consts.DEFAULT_COIN else amount
    )
    for utxo in utxos:
        # if we were able to collect exact amount, no change is needed
        if collected_amount == amount:
            break
        # make sure the change is higher than `_min_change_value`
        if collected_amount >= amount_plus_change:
            break
        collected_utxos.append(utxo)
        collected_amount += utxo.amount

    return collected_utxos


def _select_utxos(
    txins_db: Dict[str, List[structs.UTXOData]],
    txouts_passed_db: Dict[str, List[structs.TxOut]],
    txouts_mint_db: Dict[str, List[structs.TxOut]],
    fee: int,
    withdrawals: structs.OptionalTxOuts,
    min_change_value: int,
    deposit: int = 0,
) -> Set[str]:
    """Select UTxOs that can satisfy all outputs, deposits and fee.

    Return IDs of selected UTxOs.
    """
    utxo_ids: Set[str] = set()

    # iterate over coins both in txins and txouts
    for coin in set(txins_db).union(txouts_passed_db).union(txouts_mint_db):
        coin_txins = txins_db.get(coin) or []
        coin_txouts = txouts_passed_db.get(coin) or []

        total_output_amount = functools.reduce(lambda x, y: x + y.amount, coin_txouts, 0)

        if coin == consts.DEFAULT_COIN:
            # the value "-1" means all available funds
            max_index = [idx for idx, val in enumerate(coin_txouts) if val.amount == -1]
            if max_index:
                utxo_ids.update(f"{rec.utxo_hash}#{rec.utxo_ix}" for rec in coin_txins)
                continue

            tx_fee = fee if fee > 1 else 1
            funds_needed = total_output_amount + tx_fee + deposit
            total_withdrawals_amount = functools.reduce(lambda x, y: x + y.amount, withdrawals, 0)
            # fee needs an input, even if withdrawal would cover all needed funds
            input_funds_needed = max(funds_needed - total_withdrawals_amount, tx_fee)
        else:
            coin_txouts_minted = txouts_mint_db.get(coin) or []
            total_minted_amount = functools.reduce(lambda x, y: x + y.amount, coin_txouts_minted, 0)
            # In case of token burning, `total_minted_amount` might be negative.
            # Try to collect enough funds to satisfy both token burning and token
            # transfers, even though there might be an overlap.
            input_funds_needed = total_output_amount - total_minted_amount

        filtered_coin_utxos = _collect_utxos_amount(
            utxos=coin_txins, amount=input_funds_needed, min_change_value=min_change_value
        )
        utxo_ids.update(f"{rec.utxo_hash}#{rec.utxo_ix}" for rec in filtered_coin_utxos)

    return utxo_ids


def _balance_txouts(  # noqa: C901
    change_address: str,
    txouts: structs.OptionalTxOuts,
    txins_db: Dict[str, List[structs.UTXOData]],
    txouts_passed_db: Dict[str, List[structs.TxOut]],
    txouts_mint_db: Dict[str, List[structs.TxOut]],
    fee: int,
    withdrawals: structs.OptionalTxOuts,
    deposit: int = 0,
    lovelace_balanced: bool = False,
) -> List[structs.TxOut]:
    """Balance the transaction by adding change output for each coin."""
    # records for burning tokens, i.e. records with negative amount, are not allowed in `txouts`
    burning_txouts = [r for r in txouts if r.amount < 0 and r.coin != consts.DEFAULT_COIN]
    if burning_txouts:
        raise AssertionError(f"Token burning is not allowed in txouts: {burning_txouts}")

    txouts_result: List[structs.TxOut] = list(txouts)

    # iterate over coins both in txins and txouts
    for coin in set(txins_db).union(txouts_passed_db).union(txouts_mint_db):
        max_address = None
        change = 0

        coin_txins = txins_db.get(coin) or []
        coin_txouts = txouts_passed_db.get(coin) or []

        if coin == consts.DEFAULT_COIN:
            # the value "-1" means all available funds
            max_index = [idx for idx, val in enumerate(coin_txouts) if val.amount == -1]
            if len(max_index) > 1:
                raise AssertionError("Cannot send all remaining funds to more than one address.")
            if max_index:
                # remove the "-1" record and get its address
                max_address = coin_txouts.pop(max_index[0]).address

        total_input_amount = functools.reduce(lambda x, y: x + y.amount, coin_txins, 0)
        total_output_amount = functools.reduce(lambda x, y: x + y.amount, coin_txouts, 0)

        if coin == consts.DEFAULT_COIN and lovelace_balanced:
            # balancing is done elsewhere (by the `transaction build` command)
            pass
        elif coin == consts.DEFAULT_COIN:
            tx_fee = fee if fee > 0 else 0
            total_withdrawals_amount = functools.reduce(lambda x, y: x + y.amount, withdrawals, 0)
            funds_available = total_input_amount + total_withdrawals_amount
            funds_needed = total_output_amount + tx_fee + deposit
            change = funds_available - funds_needed
            if change < 0:
                LOGGER.error(
                    "Not enough funds to make the transaction - "
                    f"available: {funds_available}; needed: {funds_needed}"
                )
        else:
            coin_txouts_minted = txouts_mint_db.get(coin) or []
            total_minted_amount = functools.reduce(lambda x, y: x + y.amount, coin_txouts_minted, 0)
            funds_available = total_input_amount + total_minted_amount
            change = funds_available - total_output_amount
            if change < 0:
                LOGGER.error(
                    f"Amount of coin `{coin}` is not sufficient - "
                    f"available: {funds_available}; needed: {total_output_amount}"
                )

        if change > 0:
            txouts_result.append(
                structs.TxOut(address=(max_address or change_address), amount=change, coin=coin)
            )

    # filter out negative amounts (-1 "max" amounts)
    txouts_result = [r for r in txouts_result if r.amount > 0]

    return txouts_result


def _resolve_withdrawals(
    clusterlib_obj: "types.ClusterLib", withdrawals: List[structs.TxOut]
) -> List[structs.TxOut]:
    """Return list of resolved reward withdrawals.

    The `structs.TxOut.amount` can be '-1', meaning all available funds.

    Args:
        clusterlib_obj: An instance of `ClusterLib`.
        withdrawals: A list (iterable) of `TxOuts`, specifying reward withdrawals.

    Returns:
        List[structs.TxOut]: A list of `TxOuts`, specifying resolved reward withdrawals.
    """
    resolved_withdrawals = []
    for rec in withdrawals:
        # the amount with value "-1" means all available balance
        if rec.amount == -1:
            balance = clusterlib_obj.g_query.get_stake_addr_info(rec.address).reward_account_balance
            resolved_withdrawals.append(structs.TxOut(address=rec.address, amount=balance))
        else:
            resolved_withdrawals.append(rec)

    return resolved_withdrawals


def _get_withdrawals(
    clusterlib_obj: "types.ClusterLib",
    withdrawals: structs.OptionalTxOuts,
    script_withdrawals: structs.OptionalScriptWithdrawals,
) -> Tuple[structs.OptionalTxOuts, structs.OptionalScriptWithdrawals, structs.OptionalTxOuts]:
    """Return tuple of resolved withdrawals.

    Return simple withdrawals, script withdrawals, combination of all withdrawals Tx outputs.
    """
    withdrawals = withdrawals and _resolve_withdrawals(
        clusterlib_obj=clusterlib_obj, withdrawals=withdrawals
    )
    script_withdrawals = [
        s._replace(
            txout=_resolve_withdrawals(clusterlib_obj=clusterlib_obj, withdrawals=[s.txout])[0]
        )
        for s in script_withdrawals
    ]
    withdrawals_txouts = [*withdrawals, *[s.txout for s in script_withdrawals]]
    return withdrawals, script_withdrawals, withdrawals_txouts


def _get_txin_strings(
    txins: structs.OptionalUTXOData, script_txins: structs.OptionalScriptTxIn
) -> Set[str]:
    """Get list of txin strings for normal (non-script) inputs."""
    # filter out duplicate txins
    txins_utxos = {f"{x.utxo_hash}#{x.utxo_ix}" for x in txins}

    # assume that all plutus txin records are for the same UTxO and use the first one
    plutus_txins_utxos = {
        f"{x.txins[0].utxo_hash}#{x.txins[0].utxo_ix}" for x in script_txins if x.txins
    }

    # remove plutus txin records from normal txins
    txins_combined = txins_utxos.difference(plutus_txins_utxos)

    return txins_combined


def _get_txout_plutus_args(txout: structs.TxOut) -> List[str]:  # noqa: C901
    txout_args = []

    # add datum arguments
    if txout.datum_hash:
        txout_args = [
            "--tx-out-datum-hash",
            str(txout.datum_hash),
        ]
    elif txout.datum_hash_file:
        txout_args = [
            "--tx-out-datum-hash-file",
            str(txout.datum_hash_file),
        ]
    elif txout.datum_hash_cbor_file:
        txout_args = [
            "--tx-out-datum-hash-cbor-file",
            str(txout.datum_hash_cbor_file),
        ]
    elif txout.datum_hash_value:
        txout_args = [
            "--tx-out-datum-hash-value",
            str(txout.datum_hash_value),
        ]
    elif txout.datum_embed_file:
        txout_args = [
            "--tx-out-datum-embed-file",
            str(txout.datum_embed_file),
        ]
    elif txout.datum_embed_cbor_file:
        txout_args = [
            "--tx-out-datum-embed-cbor-file",
            str(txout.datum_embed_cbor_file),
        ]
    elif txout.datum_embed_value:
        txout_args = [
            "--tx-out-datum-embed-value",
            str(txout.datum_embed_value),
        ]
    elif txout.inline_datum_file:
        txout_args = [
            "--tx-out-inline-datum-file",
            str(txout.inline_datum_file),
        ]
    elif txout.inline_datum_cbor_file:
        txout_args = [
            "--tx-out-inline-datum-cbor-file",
            str(txout.inline_datum_cbor_file),
        ]
    elif txout.inline_datum_value:
        txout_args = [
            "--tx-out-inline-datum-value",
            str(txout.inline_datum_value),
        ]

    # add reference script arguments
    if txout.reference_script_file:
        txout_args.extend(
            [
                "--tx-out-reference-script-file",
                str(txout.reference_script_file),
            ]
        )

    return txout_args


def get_joined_txouts(
    txouts: List[structs.TxOut],
) -> List[List[structs.TxOut]]:
    """Return list of joined `TxOut`s."""
    txouts_by_eutxo_attrs: Dict[str, List[structs.TxOut]] = {}
    joined_txouts: List[List[structs.TxOut]] = []

    # aggregate TX outputs by address, datum and reference script
    for rec in txouts:
        datum_src = str(
            rec.datum_hash
            or rec.datum_hash_file
            or rec.datum_hash_cbor_file
            or rec.datum_hash_value
            or rec.datum_embed_file
            or rec.datum_embed_cbor_file
            or rec.datum_embed_value
        )

        inline_datum_src = str(
            rec.inline_datum_file or rec.inline_datum_cbor_file or rec.inline_datum_value
        )

        eutxo_attrs = f"{rec.address}::{datum_src}::{inline_datum_src}::{rec.reference_script_file}"

        if eutxo_attrs not in txouts_by_eutxo_attrs:
            txouts_by_eutxo_attrs[eutxo_attrs] = []
        txouts_by_eutxo_attrs[eutxo_attrs].append(rec)

    # join txouts with the same address, datum and reference script
    for txouts_list in txouts_by_eutxo_attrs.values():
        # create single `TxOut` record with sum of amounts per coin
        txouts_by_coin: Dict[str, Tuple[structs.TxOut, List[int]]] = {}
        for ar in txouts_list:
            if ar.coin in txouts_by_coin:
                txouts_by_coin[ar.coin][1].append(ar.amount)
            else:
                txouts_by_coin[ar.coin] = (ar, [ar.amount])
        # The tuple for each coin is `("one of the original TxOuts", "list of amounts")`.
        # All the `TxOut` values except of amount are the same in this loop, so we can
        # take the original `TxOut` and replace `amount` with sum of all amounts.
        sum_txouts = [r[0]._replace(amount=sum(r[1])) for r in txouts_by_coin.values()]

        joined_txouts.append(sum_txouts)

    return joined_txouts


def _join_txouts(
    txouts: List[structs.TxOut],
) -> Tuple[List[str], List[structs.TxOut], int]:
    txout_args: List[str] = []
    joined_txouts = get_joined_txouts(txouts=txouts)
    for joined_recs in joined_txouts:
        amounts = [
            f"{r.amount} {r.coin if r.coin != consts.DEFAULT_COIN else ''}".rstrip()
            for r in joined_recs
        ]
        amounts_joined = "+".join(amounts)

        txout_args.extend(["--tx-out", f"{joined_recs[0].address}+{amounts_joined}"])
        txout_args.extend(_get_txout_plutus_args(txout=joined_recs[0]))

    joined_txouts_flat = list(itertools.chain.from_iterable(joined_txouts))
    return txout_args, joined_txouts_flat, len(joined_txouts)


def _list_txouts(txouts: List[structs.TxOut]) -> List[str]:
    txout_args: List[str] = []

    for rec in txouts:
        txout_args.extend(
            [
                "--tx-out",
                f"{rec.address}+{rec.amount} "
                f"{rec.coin if rec.coin != consts.DEFAULT_COIN else ''}".rstrip(),
            ]
        )
        txout_args.extend(_get_txout_plutus_args(txout=rec))

    return txout_args


def _get_return_collateral_txout_args(txouts: structs.OptionalTxOuts) -> List[str]:
    if not txouts:
        return []

    addresses = {t.address for t in txouts}
    if len(addresses) > 1:
        raise AssertionError("Accepts `txouts` only for single address.")

    txout_records = [
        f"{t.amount} {t.coin if t.coin != consts.DEFAULT_COIN else ''}".rstrip() for t in txouts
    ]
    # pylint: disable=consider-using-f-string
    address_value = "{}+{}".format(txouts[0].address, "+".join(txout_records))
    txout_args = ["--tx-out-return-collateral", address_value]

    return txout_args


def _process_txouts(
    txouts: List[structs.TxOut], join_txouts: bool
) -> Tuple[List[str], List[structs.TxOut], int]:
    if join_txouts:
        return _join_txouts(txouts=txouts)
    return _list_txouts(txouts=txouts), txouts, len(txouts)


def _get_tx_ins_outs(
    clusterlib_obj: "types.ClusterLib",
    src_address: str,
    tx_files: structs.TxFiles,
    txins: structs.OptionalUTXOData = (),
    txouts: structs.OptionalTxOuts = (),
    fee: int = 0,
    deposit: Optional[int] = None,
    withdrawals: structs.OptionalTxOuts = (),
    mint_txouts: structs.OptionalTxOuts = (),
    lovelace_balanced: bool = False,
) -> Tuple[List[structs.UTXOData], List[structs.TxOut]]:
    """Return list of transaction's inputs and outputs.

    Args:
        clusterlib_obj: An instance of `ClusterLib`.
        src_address: An address used for fee and inputs (if inputs not specified by `txins`).
        tx_files: A `structs.TxFiles` tuple containing files needed for the transaction.
        txins: An iterable of `structs.UTXOData`, specifying input UTxOs (optional).
        txouts: A list (iterable) of `TxOuts`, specifying transaction outputs (optional).
        fee: A fee amount (optional).
        deposit: A deposit amount needed by the transaction (optional).
        withdrawals: A list (iterable) of `TxOuts`, specifying reward withdrawals (optional).
        mint_txouts: A list (iterable) of `TxOuts`, specifying minted tokens (optional).

    Returns:
        Tuple[list, list]: A tuple of list of transaction inputs and list of transaction
            outputs.
    """
    txouts_passed_db: Dict[str, List[structs.TxOut]] = _organize_tx_ins_outs_by_coin(txouts)
    txouts_mint_db: Dict[str, List[structs.TxOut]] = _organize_tx_ins_outs_by_coin(mint_txouts)
    outcoins_all = {consts.DEFAULT_COIN, *txouts_mint_db.keys(), *txouts_passed_db.keys()}
    outcoins_passed = [consts.DEFAULT_COIN, *txouts_passed_db.keys()]

    txins_all = list(txins)
    if not txins_all:
        # no txins were provided, so we'll select them from the source address
        address_utxos = clusterlib_obj.g_query.get_utxo(address=src_address)
        if not address_utxos:
            raise exceptions.CLIError(f"No UTxO returned for '{src_address}'.")
        txins_all = _get_usable_utxos(address_utxos=address_utxos, coins=outcoins_all)

    if not txins_all:
        raise exceptions.CLIError("No input UTxO.")

    txins_db_all: Dict[str, List[structs.UTXOData]] = _organize_tx_ins_outs_by_coin(txins_all)

    # all output coins, except those minted by this transaction, need to be present in
    # transaction inputs
    if not set(outcoins_passed).difference(txouts_mint_db).issubset(txins_db_all):
        raise exceptions.CLIError("Not all output coins are present in input UTxOs.")

    tx_deposit = (
        clusterlib_obj.g_transaction.get_tx_deposit(tx_files=tx_files)
        if deposit is None
        else deposit
    )

    if txins:
        # don't touch txins that were passed to the function
        txins_filtered = txins_all
        txins_db_filtered = txins_db_all
    else:
        # select only UTxOs that are needed to satisfy all outputs, deposits and fee
        selected_utxo_ids = _select_utxos(
            txins_db=txins_db_all,
            txouts_passed_db=txouts_passed_db,
            txouts_mint_db=txouts_mint_db,
            fee=fee,
            withdrawals=withdrawals,
            min_change_value=clusterlib_obj._min_change_value,
            deposit=tx_deposit,
        )
        txins_by_id: Dict[str, List[structs.UTXOData]] = _organize_utxos_by_id(txins_all)
        _txins_filtered = [utxo for uid, utxo in txins_by_id.items() if uid in selected_utxo_ids]

        txins_filtered = list(itertools.chain.from_iterable(_txins_filtered))
        txins_db_filtered = _organize_tx_ins_outs_by_coin(txins_filtered)

    if not txins_filtered:
        raise exceptions.CLIError("Cannot build transaction, empty `txins`.")

    # balance the transaction
    txouts_balanced = _balance_txouts(
        # Return change to `src_address`.
        # When using `build_tx`, Lovelace change is returned to `change_address` (this is handled
        # automatically by `transaction build`) and only tokens change is returned to
        # `src_address`. It is up to user to specify Lovelace output for `src_address` with high
        # enough Lovelace value when token change is needed and `change_address` differs from
        # `src_address`.
        change_address=src_address,
        txouts=txouts,
        txins_db=txins_db_filtered,
        txouts_passed_db=txouts_passed_db,
        txouts_mint_db=txouts_mint_db,
        fee=fee,
        withdrawals=withdrawals,
        deposit=tx_deposit,
        lovelace_balanced=lovelace_balanced,
    )

    return txins_filtered, txouts_balanced


def collect_data_for_build(
    clusterlib_obj: "types.ClusterLib",
    src_address: str,
    txins: structs.OptionalUTXOData = (),
    txouts: structs.OptionalTxOuts = (),
    script_txins: structs.OptionalScriptTxIn = (),
    mint: structs.OptionalMint = (),
    tx_files: Optional[structs.TxFiles] = None,
    complex_certs: structs.OptionalScriptCerts = (),
    fee: int = 0,
    withdrawals: structs.OptionalTxOuts = (),
    script_withdrawals: structs.OptionalScriptWithdrawals = (),
    deposit: Optional[int] = None,
    lovelace_balanced: bool = False,
) -> structs.DataForBuild:
    """Collect data (txins, txouts, withdrawals) needed for building a transaction.

    Args:
        clusterlib_obj: An instance of `ClusterLib`.
        src_address: An address used for fee and inputs (if inputs not specified by `txins`).
        txins: An iterable of `structs.UTXOData`, specifying input UTxOs (optional).
        txouts: A list (iterable) of `TxOuts`, specifying transaction outputs (optional).
        script_txins: An iterable of `ScriptTxIn`, specifying input script UTxOs (optional).
        mint: An iterable of `Mint`, specifying script minting data (optional).
        tx_files: A `structs.TxFiles` tuple containing files needed for the transaction
            (optional).
        complex_certs: An iterable of `ComplexCert`, specifying certificates script data
            (optional).
        fee: A fee amount (optional).
        withdrawals: A list (iterable) of `TxOuts`, specifying reward withdrawals (optional).
        script_withdrawals: An iterable of `ScriptWithdrawal`, specifying withdrawal script
            data (optional).
        deposit: A deposit amount needed by the transaction (optional).
        lovelace_balanced: A bool indicating whether Lovelace ins/outs are balanced
            (by `build` command; optional)

    Returns:
        structs.DataForBuild: A tuple with data for build(-raw) commands.
    """
    # pylint: disable=too-many-arguments
    tx_files = tx_files or structs.TxFiles()

    withdrawals, script_withdrawals, withdrawals_txouts = _get_withdrawals(
        clusterlib_obj=clusterlib_obj,
        withdrawals=withdrawals,
        script_withdrawals=script_withdrawals,
    )

    script_txins_records = list(itertools.chain.from_iterable(r.txins for r in script_txins))

    script_addresses = {r.address for r in script_txins_records}
    if src_address in script_addresses:
        raise AssertionError("Source address cannot be a script address.")

    # combine txins and make sure we have enough funds to satisfy all txouts
    combined_txins = [
        *txins,
        *script_txins_records,
    ]
    mint_txouts = list(itertools.chain.from_iterable(m.txouts for m in mint))
    combined_tx_files = tx_files._replace(
        certificate_files=[
            *tx_files.certificate_files,
            *[c.certificate_file for c in complex_certs],
        ]
    )
    txins_copy, txouts_copy = _get_tx_ins_outs(
        clusterlib_obj=clusterlib_obj,
        src_address=src_address,
        tx_files=combined_tx_files,
        txins=combined_txins,
        txouts=txouts,
        fee=fee,
        deposit=deposit,
        withdrawals=withdrawals_txouts,
        mint_txouts=mint_txouts,
        lovelace_balanced=lovelace_balanced,
    )

    payment_txins = txins or txins_copy
    # don't include script txins in list of payment txins
    if script_txins_records:
        payment_txins = txins or []

    return structs.DataForBuild(
        txins=payment_txins,
        txouts=txouts_copy,
        withdrawals=withdrawals,
        script_withdrawals=script_withdrawals,
    )


def get_utxo(
    utxo_dict: dict,
    address: str = "",
    coins: types.UnpackableSequence = (),
) -> List[structs.UTXOData]:
    """Return UTxO info for payment address.

    Args:
        utxo_dict: A JSON output of `query utxo`.
        address: A payment address.
        coins: A list (iterable) of coin names (asset IDs).

    Returns:
        List[structs.UTXOData]: A list of UTxO data.
    """
    utxo = []
    for utxo_rec, utxo_data in utxo_dict.items():
        utxo_hash, utxo_ix = utxo_rec.split("#")
        utxo_address = utxo_data.get("address") or ""
        addr_data = utxo_data["value"]
        datum_hash = utxo_data.get("data") or utxo_data.get("datumhash") or ""
        inline_datum_hash = utxo_data.get("inlineDatumhash") or ""
        inline_datum = utxo_data.get("inlineDatum")
        reference_script = utxo_data.get("referenceScript")

        for policyid, coin_data in addr_data.items():
            if policyid == consts.DEFAULT_COIN:
                utxo.append(
                    structs.UTXOData(
                        utxo_hash=utxo_hash,
                        utxo_ix=int(utxo_ix),
                        amount=coin_data,
                        address=address or utxo_address,
                        coin=consts.DEFAULT_COIN,
                        datum_hash=datum_hash,
                        inline_datum_hash=inline_datum_hash,
                        inline_datum=inline_datum,
                        reference_script=reference_script,
                    )
                )
                continue

            # coin data used to be a dict, now it is a list
            try:
                coin_iter = coin_data.items()
            except AttributeError:
                coin_iter = coin_data

            for asset_name, amount in coin_iter:
                decoded_coin = ""
                if asset_name:
                    with contextlib.suppress(Exception):
                        decoded_name = base64.b16decode(asset_name.encode(), casefold=True).decode(
                            "utf-8"
                        )
                        decoded_coin = f"{policyid}.{decoded_name}"
                else:
                    decoded_coin = policyid

                utxo.append(
                    structs.UTXOData(
                        utxo_hash=utxo_hash,
                        utxo_ix=int(utxo_ix),
                        amount=amount,
                        address=address or utxo_address,
                        coin=f"{policyid}.{asset_name}" if asset_name else policyid,
                        decoded_coin=decoded_coin,
                        datum_hash=datum_hash,
                        inline_datum_hash=inline_datum_hash,
                        inline_datum=inline_datum,
                        reference_script=reference_script,
                    )
                )

    if coins:
        filtered_utxo = [u for u in utxo if u.coin in coins]
        return filtered_utxo

    return utxo


def calculate_utxos_balance(
    utxos: Union[List[structs.UTXOData], List[structs.TxOut]], coin: str = consts.DEFAULT_COIN
) -> int:
    """Calculate sum of UTxO balances.

    Args:
        utxos: A list of UTxO data (either `structs.UTXOData` or `structs.TxOut`).
        coin: A coin name (asset IDs).

    Returns:
        int: A total balance.
    """
    filtered_utxos = [u for u in utxos if u.coin == coin]
    address_balance = functools.reduce(lambda x, y: x + y.amount, filtered_utxos, 0)
    return int(address_balance)


def filter_utxo_with_highest_amount(
    utxos: List[structs.UTXOData],
    coin: str = consts.DEFAULT_COIN,
) -> structs.UTXOData:
    """Return data for UTxO with the highest amount.

    Args:
        utxos: A list of UTxO data.
        coin: A coin name (asset IDs).

    Returns:
        structs.UTXOData: An UTxO record with the highest amount.
    """
    filtered_utxos = [u for u in utxos if u.coin == coin]
    highest_amount_rec = max(filtered_utxos, key=lambda x: x.amount)
    return highest_amount_rec


def filter_utxos(
    utxos: List[structs.UTXOData],
    utxo_hash: str = "",
    utxo_ix: Optional[int] = None,
    amount: Optional[int] = None,
    address: str = "",
    coin: str = "",
    datum_hash: str = "",
    inline_datum_hash: str = "",
) -> List[structs.UTXOData]:
    """Get UTxO records that match given filtering criteria.

    Args:
        utxos: A list of UTxO data.
        utxo_hash: A transaction identifier (optional).
        utxo_ix: A UTxO index (optional).
        amount: An amount of coin (optional).
        address: A payment address (optional).
        coin: A coin name (asset ID; optional).
        datum_hash: A datum hash (optional).
        inline_datum_hash: An inline datum hash (optional).

    Returns:
        structs.UTXOData: UTxO records that match given filtering criteria.
    """
    filtered_utxos = []

    for u in utxos:
        if utxo_hash and u.utxo_hash != utxo_hash:
            continue
        if utxo_ix is not None and utxo_ix != u.utxo_ix:
            continue
        if amount is not None and amount != u.amount:
            continue
        if address and u.address != address:
            continue
        if coin and u.coin != coin:
            continue
        if datum_hash and u.datum_hash != datum_hash:
            continue
        if inline_datum_hash and u.inline_datum_hash != inline_datum_hash:
            continue
        filtered_utxos.append(u)

    return filtered_utxos


def _get_script_args(  # noqa: C901
    script_txins: structs.OptionalScriptTxIn,
    mint: structs.OptionalMint,
    complex_certs: structs.OptionalScriptCerts,
    script_withdrawals: structs.OptionalScriptWithdrawals,
    for_build: bool = True,
) -> List[str]:
    # pylint: disable=too-many-statements,too-many-branches
    grouped_args: List[str] = []
    collaterals_all = set()

    # spending
    for tin in script_txins:
        if tin.txins:
            grouped_args.extend(
                [
                    "--tx-in",
                    # assume that all txin records are for the same UTxO and use the first one
                    f"{tin.txins[0].utxo_hash}#{tin.txins[0].utxo_ix}",
                ]
            )
        tin_collaterals = {f"{c.utxo_hash}#{c.utxo_ix}" for c in tin.collaterals}
        collaterals_all.update(tin_collaterals)

        if tin.script_file:
            grouped_args.extend(
                [
                    "--tx-in-script-file",
                    str(tin.script_file),
                ]
            )

            if not for_build and tin.execution_units:
                grouped_args.extend(
                    [
                        "--tx-in-execution-units",
                        f"({tin.execution_units[0]},{tin.execution_units[1]})",
                    ]
                )

            if tin.datum_file:
                grouped_args.extend(["--tx-in-datum-file", str(tin.datum_file)])
            if tin.datum_cbor_file:
                grouped_args.extend(["--tx-in-datum-cbor-file", str(tin.datum_cbor_file)])
            if tin.datum_value:
                grouped_args.extend(["--tx-in-datum-value", str(tin.datum_value)])
            if tin.inline_datum_present:
                grouped_args.append("--tx-in-inline-datum-present")
            if tin.redeemer_file:
                grouped_args.extend(["--tx-in-redeemer-file", str(tin.redeemer_file)])
            if tin.redeemer_cbor_file:
                grouped_args.extend(["--tx-in-redeemer-cbor-file", str(tin.redeemer_cbor_file)])
            if tin.redeemer_value:
                grouped_args.extend(["--tx-in-redeemer-value", str(tin.redeemer_value)])

        if tin.reference_txin:
            tin_reference_txin_id = f"{tin.reference_txin.utxo_hash}#{tin.reference_txin.utxo_ix}"
            tin_reference_type = tin.reference_type or consts.ScriptTypes.PLUTUS_V2

            if tin_reference_type in (consts.ScriptTypes.SIMPLE_V1, consts.ScriptTypes.SIMPLE_V2):
                grouped_args.extend(
                    [
                        "--simple-script-tx-in-reference",
                        tin_reference_txin_id,
                    ]
                )
            else:
                grouped_args.extend(
                    [
                        "--spending-tx-in-reference",
                        tin_reference_txin_id,
                    ]
                )

            if tin.reference_type == consts.ScriptTypes.PLUTUS_V2:
                grouped_args.append("--spending-plutus-script-v2")

            if not for_build and tin.execution_units:
                grouped_args.extend(
                    [
                        "--spending-reference-tx-in-execution-units",
                        f"({tin.execution_units[0]},{tin.execution_units[1]})",
                    ]
                )

            if tin.datum_file:
                grouped_args.extend(["--spending-reference-tx-in-datum-file", str(tin.datum_file)])
            if tin.datum_cbor_file:
                grouped_args.extend(
                    ["--spending-reference-tx-in-datum-cbor-file", str(tin.datum_cbor_file)]
                )
            if tin.datum_value:
                grouped_args.extend(
                    ["--spending-reference-tx-in-datum-value", str(tin.datum_value)]
                )
            if tin.inline_datum_present:
                grouped_args.append("--spending-reference-tx-in-inline-datum-present")
            if tin.redeemer_file:
                grouped_args.extend(
                    ["--spending-reference-tx-in-redeemer-file", str(tin.redeemer_file)]
                )
            if tin.redeemer_cbor_file:
                grouped_args.extend(
                    ["--spending-reference-tx-in-redeemer-cbor-file", str(tin.redeemer_cbor_file)]
                )
            if tin.redeemer_value:
                grouped_args.extend(
                    ["--spending-reference-tx-in-redeemer-value", str(tin.redeemer_value)]
                )

    # minting
    for mrec in mint:
        mrec_collaterals = {f"{c.utxo_hash}#{c.utxo_ix}" for c in mrec.collaterals}
        collaterals_all.update(mrec_collaterals)

        if mrec.script_file:
            grouped_args.extend(
                [
                    "--mint-script-file",
                    str(mrec.script_file),
                ]
            )

            if not for_build and mrec.execution_units:
                grouped_args.extend(
                    [
                        "--mint-execution-units",
                        f"({mrec.execution_units[0]},{mrec.execution_units[1]})",
                    ]
                )

            if mrec.redeemer_file:
                grouped_args.extend(["--mint-redeemer-file", str(mrec.redeemer_file)])
            if mrec.redeemer_cbor_file:
                grouped_args.extend(["--mint-redeemer-cbor-file", str(mrec.redeemer_cbor_file)])
            if mrec.redeemer_value:
                grouped_args.extend(["--mint-redeemer-value", str(mrec.redeemer_value)])

        if mrec.reference_txin:
            mrec_reference_txin_id = (
                f"{mrec.reference_txin.utxo_hash}#{mrec.reference_txin.utxo_ix}"
            )
            mrec_reference_type = mrec.reference_type or consts.ScriptTypes.PLUTUS_V2

            if mrec_reference_type in (consts.ScriptTypes.SIMPLE_V1, consts.ScriptTypes.SIMPLE_V2):
                grouped_args.extend(
                    [
                        "--simple-minting-script-tx-in-reference",
                        mrec_reference_txin_id,
                    ]
                )
            else:
                grouped_args.extend(
                    [
                        "--mint-tx-in-reference",
                        mrec_reference_txin_id,
                    ]
                )
            if mrec_reference_type == consts.ScriptTypes.PLUTUS_V2:
                grouped_args.append("--mint-plutus-script-v2")

            if not for_build and mrec.execution_units:
                grouped_args.extend(
                    [
                        "--mint-reference-tx-in-execution-units",
                        f"({mrec.execution_units[0]},{mrec.execution_units[1]})",
                    ]
                )

            if mrec.redeemer_file:
                grouped_args.extend(
                    ["--mint-reference-tx-in-redeemer-file", str(mrec.redeemer_file)]
                )
            if mrec.redeemer_cbor_file:
                grouped_args.extend(
                    ["--mint-reference-tx-in-redeemer-cbor-file", str(mrec.redeemer_cbor_file)]
                )
            if mrec.redeemer_value:
                grouped_args.extend(
                    ["--mint-reference-tx-in-redeemer-value", str(mrec.redeemer_value)]
                )
            if mrec.policyid:
                grouped_args.extend(["--policy-id", str(mrec.policyid)])

    # certificates
    for crec in complex_certs:
        crec_collaterals = {f"{c.utxo_hash}#{c.utxo_ix}" for c in crec.collaterals}
        collaterals_all.update(crec_collaterals)
        grouped_args.extend(
            [
                "--certificate-file",
                str(crec.certificate_file),
            ]
        )

        if crec.script_file:
            grouped_args.extend(["--certificate-script-file", str(crec.script_file)])

            if not for_build and crec.execution_units:
                grouped_args.extend(
                    [
                        "--certificate-execution-units",
                        f"({crec.execution_units[0]},{crec.execution_units[1]})",
                    ]
                )

            if crec.redeemer_file:
                grouped_args.extend(["--certificate-redeemer-file", str(crec.redeemer_file)])
            if crec.redeemer_cbor_file:
                grouped_args.extend(
                    ["--certificate-redeemer-cbor-file", str(crec.redeemer_cbor_file)]
                )
            if crec.redeemer_value:
                grouped_args.extend(["--certificate-redeemer-value", str(crec.redeemer_value)])

        if crec.reference_txin:
            grouped_args.extend(
                [
                    "--certificate-tx-in-reference",
                    f"{crec.reference_txin.utxo_hash}#{crec.reference_txin.utxo_ix}",
                ]
            )

            crec_reference_type = crec.reference_type or consts.ScriptTypes.PLUTUS_V2
            if crec_reference_type == consts.ScriptTypes.PLUTUS_V2:
                grouped_args.append("--certificate-plutus-script-v2")

            if not for_build and crec.execution_units:
                grouped_args.extend(
                    [
                        "--certificate-reference-tx-in-execution-units",
                        f"({crec.execution_units[0]},{crec.execution_units[1]})",
                    ]
                )

            if crec.redeemer_file:
                grouped_args.extend(
                    ["--certificate-reference-tx-in-redeemer-file", str(crec.redeemer_file)]
                )
            if crec.redeemer_cbor_file:
                grouped_args.extend(
                    [
                        "--certificate-reference-tx-in-redeemer-cbor-file",
                        str(crec.redeemer_cbor_file),
                    ]
                )
            if crec.redeemer_value:
                grouped_args.extend(
                    ["--certificate-reference-tx-in-redeemer-value", str(crec.redeemer_value)]
                )

    # withdrawals
    for wrec in script_withdrawals:
        wrec_collaterals = {f"{c.utxo_hash}#{c.utxo_ix}" for c in wrec.collaterals}
        collaterals_all.update(wrec_collaterals)
        grouped_args.extend(
            [
                "--withdrawal",
                f"{wrec.txout.address}+{wrec.txout.amount}",
            ]
        )

        if wrec.script_file:
            grouped_args.extend(
                [
                    "--withdrawal-script-file",
                    str(wrec.script_file),
                ]
            )

            if not for_build and wrec.execution_units:
                grouped_args.extend(
                    [
                        "--withdrawal-execution-units",
                        f"({wrec.execution_units[0]},{wrec.execution_units[1]})",
                    ]
                )

            if wrec.redeemer_file:
                grouped_args.extend(["--withdrawal-redeemer-file", str(wrec.redeemer_file)])
            if wrec.redeemer_cbor_file:
                grouped_args.extend(
                    ["--withdrawal-redeemer-cbor-file", str(wrec.redeemer_cbor_file)]
                )
            if wrec.redeemer_value:
                grouped_args.extend(["--withdrawal-redeemer-value", str(wrec.redeemer_value)])

        if wrec.reference_txin:
            grouped_args.extend(
                [
                    "--withdrawal-tx-in-reference",
                    f"{wrec.reference_txin.utxo_hash}#{wrec.reference_txin.utxo_ix}",
                ]
            )

            wrec_reference_type = wrec.reference_type or consts.ScriptTypes.PLUTUS_V2
            if wrec_reference_type == consts.ScriptTypes.PLUTUS_V2:
                grouped_args.append("--withdrawal-plutus-script-v2")

            if not for_build and wrec.execution_units:
                grouped_args.extend(
                    [
                        "--withdrawal-reference-tx-in-execution-units",
                        f"({wrec.execution_units[0]},{wrec.execution_units[1]})",
                    ]
                )

            if wrec.redeemer_file:
                grouped_args.extend(
                    ["--withdrawal-reference-tx-in-redeemer-file", str(wrec.redeemer_file)]
                )
            if wrec.redeemer_cbor_file:
                grouped_args.extend(
                    [
                        "--withdrawal-reference-tx-in-redeemer-cbor-file",
                        str(wrec.redeemer_cbor_file),
                    ]
                )
            if wrec.redeemer_value:
                grouped_args.extend(
                    ["--withdrawal-reference-tx-in-redeemer-value", str(wrec.redeemer_value)]
                )

    # add unique collaterals
    grouped_args.extend(
        [
            *helpers._prepend_flag("--tx-in-collateral", collaterals_all),
        ]
    )

    return grouped_args
