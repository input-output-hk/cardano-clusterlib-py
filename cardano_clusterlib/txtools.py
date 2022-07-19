"""Tools used by `ClusterLib` for constructing transactions."""
import base64
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


def _get_utxos_with_coins(
    address_utxos: List[structs.UTXOData], coins: Set[str]
) -> List[structs.UTXOData]:
    """Get all UTxOs that contain any of the required coins (`coins`)."""
    txins_by_id = _organize_utxos_by_id(address_utxos)

    txins = []
    seen_ids = set()
    for rec in address_utxos:
        utxo_id = f"{rec.utxo_hash}#{rec.utxo_ix}"
        if rec.coin in coins and utxo_id not in seen_ids:
            seen_ids.add(utxo_id)
            txins.extend(txins_by_id[utxo_id])

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

        # the value "-1" means all available funds
        max_index = [idx for idx, val in enumerate(coin_txouts) if val.amount == -1]
        if max_index:
            utxo_ids.update(f"{rec.utxo_hash}#{rec.utxo_ix}" for rec in coin_txins)
            continue

        total_output_amount = functools.reduce(lambda x, y: x + y.amount, coin_txouts, 0)

        if coin == consts.DEFAULT_COIN:
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


def _balance_txouts(
    src_address: str,
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
    txouts_result: List[structs.TxOut] = list(txouts)

    # iterate over coins both in txins and txouts
    for coin in set(txins_db).union(txouts_passed_db).union(txouts_mint_db):
        max_address = None
        change = 0
        coin_txins = txins_db.get(coin) or []
        coin_txouts = txouts_passed_db.get(coin) or []

        # the value "-1" means all available funds
        max_index = [idx for idx, val in enumerate(coin_txouts) if val.amount == -1]
        if len(max_index) > 1:
            raise AssertionError("Cannot send all remaining funds to more than one address.")
        if max_index:
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
                structs.TxOut(address=(max_address or src_address), amount=change, coin=coin)
            )

    # filter out negative amounts (tokens burning and -1 "max" amounts)
    txouts_result = [r for r in txouts_result if r.amount > 0]

    return txouts_result


def _resolve_withdrawals(
    clusterlib_obj: "types.ClusterLib", withdrawals: List[structs.TxOut]
) -> List[structs.TxOut]:
    """Return list of resolved reward withdrawals.

    The `structs.TxOut.amount` can be '-1', meaning all available funds.

    Args:
        withdrawals: A list (iterable) of `TxOuts`, specifying reward withdrawals.

    Returns:
        List[structs.TxOut]: A list of `TxOuts`, specifying resolved reward withdrawals.
    """
    resolved_withdrawals = []
    for rec in withdrawals:
        # the amount with value "-1" means all available balance
        if rec.amount == -1:
            balance = clusterlib_obj.get_stake_addr_info(rec.address).reward_account_balance
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

    # add regerence spript arguments
    if txout.reference_script_file:
        txout_args.extend(
            [
                "--tx-out-reference-script-file",
                str(txout.reference_script_file),
            ]
        )

    return txout_args


def _join_txouts(txouts: List[structs.TxOut]) -> List[str]:
    txout_args: List[str] = []
    txouts_datum_order: List[str] = []
    txouts_by_datum: Dict[str, Dict[str, List[structs.TxOut]]] = {}

    # aggregate TX outputs by datum and address
    for rec in txouts:
        datum_src = str(
            rec.datum_hash
            or rec.datum_hash_file
            or rec.datum_hash_cbor_file
            or rec.datum_hash_value
            or rec.inline_datum_file
            or rec.inline_datum_cbor_file
            or rec.inline_datum_value
        )
        if datum_src not in txouts_datum_order:
            txouts_datum_order.append(datum_src)
        if datum_src not in txouts_by_datum:
            txouts_by_datum[datum_src] = {}
        txouts_by_addr = txouts_by_datum[datum_src]
        if rec.address not in txouts_by_addr:
            txouts_by_addr[rec.address] = []
        txouts_by_addr[rec.address].append(rec)

    # join txouts with the same address and datum
    for datum_src in txouts_datum_order:
        for addr, recs in txouts_by_datum[datum_src].items():
            amounts = [
                f"{r.amount} {r.coin if r.coin != consts.DEFAULT_COIN else ''}".rstrip()
                for r in recs
            ]
            amounts_joined = "+".join(amounts)

            txout_args.extend(["--tx-out", f"{addr}+{amounts_joined}"])
            txout_args.extend(_get_txout_plutus_args(txout=recs[0]))

    return txout_args


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


def _process_txouts(txouts: List[structs.TxOut], join_txouts: bool) -> List[str]:
    if join_txouts:
        return _join_txouts(txouts=txouts)
    return _list_txouts(txouts=txouts)


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

    txins_all = list(txins) or _get_utxos_with_coins(
        address_utxos=clusterlib_obj.get_utxo(address=src_address), coins=outcoins_all
    )
    txins_db_all: Dict[str, List[structs.UTXOData]] = _organize_tx_ins_outs_by_coin(txins_all)

    tx_deposit = clusterlib_obj.get_tx_deposit(tx_files=tx_files) if deposit is None else deposit

    if not txins_all:
        LOGGER.error("No input UTxO.")
    # all output coins, except those minted by this transaction, need to be present in
    # transaction inputs
    elif not set(outcoins_passed).difference(txouts_mint_db).issubset(txins_db_all):
        LOGGER.error("Not all output coins are present in input UTxO.")

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
        LOGGER.error("Cannot build transaction, empty `txins`.")

    # balance the transaction
    txouts_balanced = _balance_txouts(
        src_address=src_address,
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


def get_utxo(  # noqa: C901
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
                    try:
                        decoded_name = base64.b16decode(asset_name.encode(), casefold=True).decode(
                            "utf-8"
                        )
                        decoded_coin = f"{policyid}.{decoded_name}"
                    except Exception:
                        pass
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
    """Return data for UTxO with highest amount.

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
        if utxo_ix and utxo_ix != u.utxo_ix:
            continue
        if amount and amount != u.amount:
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
        grouped_args.extend(
            [
                *helpers._prepend_flag("--tx-in-collateral", tin_collaterals),
            ]
        )

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
        grouped_args.extend(
            [
                *helpers._prepend_flag("--tx-in-collateral", mrec_collaterals),
            ]
        )

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
            grouped_args.extend(
                [
                    "--mint-tx-in-reference",
                    f"{mrec.reference_txin.utxo_hash}#{mrec.reference_txin.utxo_ix}",
                ]
            )

            mrec_reference_type = mrec.reference_type or consts.ScriptTypes.PLUTUS_V2
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
        grouped_args.extend(
            [
                *helpers._prepend_flag("--tx-in-collateral", crec_collaterals),
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
                        "--certificate-reference-execution-units",
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
        grouped_args.extend(
            [
                *helpers._prepend_flag("--tx-in-collateral", wrec_collaterals),
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
                        "--withdrawal-reference-execution-units",
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

    return grouped_args
