# README for cardano-clusterlib

[![CodeQL](https://github.com/input-output-hk/cardano-clusterlib-py/actions/workflows/codeql.yml/badge.svg)](https://github.com/input-output-hk/cardano-clusterlib-py/actions)
[![Documentation Status](https://readthedocs.org/projects/cardano-clusterlib-py/badge/?version=latest)](https://cardano-clusterlib-py.readthedocs.io/en/latest/?badge=latest)
[![PyPi Version](https://img.shields.io/pypi/v/cardano-clusterlib.svg)](https://pypi.org/project/cardano-clusterlib/)

Python wrapper for cardano-cli for working with cardano cluster. It supports all cardano-cli commands (except parts of `genesis` and `governance`).

The library is used for development of [cardano-node system tests](https://github.com/input-output-hk/cardano-node-tests).

## Installation

```sh
# create and activate virtual env
$ python3 -m venv .env
$ . .env/bin/activate
# install cardano-clusterlib from PyPI
$ pip install cardano-clusterlib
# - OR - install cardano-clusterlib in development mode together with dev requirements
$ make install
```

## Usage

The library needs working `cardano-cli` (the command is available on `PATH`, `cardano-node` is running, `CARDANO_NODE_SOCKET_PATH` is set). In `state_dir` it expects "shelley/genesis.json".

```python
# instantiate `ClusterLib`
cluster = clusterlib.ClusterLib(state_dir="path/to/cluster/state_dir")
```

### Transfer funds

```python
from cardano_clusterlib import clusterlib

# instantiate `ClusterLib`
cluster = clusterlib.ClusterLib(state_dir="path/to/cluster/state_dir")

src_address = "addr_test1vpst87uzwafqkxumyf446zr2jsyn44cfpu9fe8yqanyuh6glj2hkl"
src_skey_file = "/path/to/skey"

dst_addr = cluster.g_address.gen_payment_addr_and_keys(name="destination_address")
amount_lovelace = 10_000_000  # 10 ADA

# specify where to send funds and amounts to send
txouts = [clusterlib.TxOut(address=dst_addr.address, amount=amount_lovelace)]

# provide keys needed for signing the transaction
tx_files = clusterlib.TxFiles(signing_key_files=[src_skey_file])

# build, sign and submit the transaction
tx_raw_output = cluster.g_transaction.send_tx(
    src_address=src_address,
    tx_name="send_funds",
    txouts=txouts,
    tx_files=tx_files,
)

# check that the funds were received
cluster.g_query.get_utxo(dst_addr.address)
```

### Lock and redeem funds with Plutus script

```python
from cardano_clusterlib import clusterlib

# instantiate `ClusterLib`
cluster = clusterlib.ClusterLib(state_dir="path/to/cluster/state_dir")

# source address - for funding
src_address = "addr_test1vpst87uzwafqkxumyf446zr2jsyn44cfpu9fe8yqanyuh6glj2hkl"
src_skey_file = "/path/to/skey"

# destination address - for redeeming
dst_addr = cluster.g_address.gen_payment_addr_and_keys(name="destination_address")

amount_fund = 10_000_000  # 10 ADA
amount_redeem = 5_000_000  # 5 ADA

# get address of the Plutus script
script_address = cluster.g_address.gen_payment_addr(
    addr_name="script_address", payment_script_file="path/to/script.plutus"
)

# create a Tx output with a datum hash at the script address

# provide keys needed for signing the transaction
tx_files_fund = clusterlib.TxFiles(signing_key_files=[src_skey_file])

# get datum hash
datum_hash = cluster.g_transaction.get_hash_script_data(script_data_file="path/to/file.datum")

# specify Tx outputs for script address and collateral
txouts_fund = [
    clusterlib.TxOut(address=script_address, amount=amount_fund, datum_hash=datum_hash),
    # for collateral
    clusterlib.TxOut(address=dst_addr.address, amount=2_000_000),
]

# build and submit the Tx
tx_output_fund = cluster.g_transaction.build_tx(
    src_address=src_address,
    tx_name="fund_script_address",
    tx_files=tx_files_fund,
    txouts=txouts_fund,
    fee_buffer=2_000_000,
)
tx_signed_fund = cluster.g_transaction.sign_tx(
    tx_body_file=tx_output_fund.out_file,
    signing_key_files=tx_files_fund.signing_key_files,
    tx_name="fund_script_address",
)
cluster.g_transaction.submit_tx(tx_file=tx_signed_fund, txins=tx_output_fund.txins)

# get newly created UTxOs
fund_utxos = cluster.g_query.get_utxo(tx_raw_output=tx_output_fund)
script_utxos = clusterlib.filter_utxos(utxos=fund_utxos, address=script_address)
collateral_utxos = clusterlib.filter_utxos(utxos=fund_utxos, address=dst_addr.address)

# redeem the locked UTxO

plutus_txins = [
    clusterlib.ScriptTxIn(
        txins=script_utxos,
        script_file="path/to/script.plutus",
        collaterals=collateral_utxos,
        datum_file="path/to/file.datum",
        redeemer_file="path/to/file.redeemer",
    )
]

tx_files_redeem = clusterlib.TxFiles(signing_key_files=[dst_addr.skey_file])

txouts_redeem = [
    clusterlib.TxOut(address=dst_addr.address, amount=amount_redeem),
]

# The entire locked UTxO will be spent and fees will be covered from the locked UTxO.
# One UTxO with "amount_redeem" amount will be created on "destination address".
# Second UTxO with change will be created on "destination address".
tx_output_redeem = cluster.g_transaction.build_tx(
    src_address=src_address,  # this will not be used, because txins (`script_txins`) are specified explicitly
    tx_name="redeem_funds",
    tx_files=tx_files_redeem,
    txouts=txouts_redeem,
    script_txins=plutus_txins,
    change_address=dst_addr.address,
)
tx_signed_redeem = cluster.g_transaction.sign_tx(
    tx_body_file=tx_output_redeem.out_file,
    signing_key_files=tx_files_redeem.signing_key_files,
    tx_name="redeem_funds",
)
cluster.g_transaction.submit_tx(tx_file=tx_signed_redeem, txins=tx_output_fund.txins)
```

### Dijkstra sub-transactions

Use a CLI with `dijkstra sub-transaction` support and instantiate `ClusterLib` with
`command_era="dijkstra"`. The `latest` alias may still select Conway.

```python
# Build with explicit inputs and outputs. No change output or fee is added here.
child = cluster.g_sub_transaction.build_raw_tx_bare(
    out_file="payment_sub_tx.body",
    txins=child_inputs,
    txouts=child_outputs,
    guards=[clusterlib.TxGuard(key_hash=approval_key_hash)],
)
signed_child = cluster.g_sub_transaction.sign_tx(
    sub_tx_file=child.out_file,
    tx_name="payment",
    signing_key_files=child_signing_keys,
)

# Balance the whole batch. The parent's change accounts for the child's net value.
parent = cluster.g_transaction.build_raw_tx(
    src_address=fee_address,
    tx_name="batch",
    fee=parent_fee,
    sub_transactions=[clusterlib.SignedSubTx(out_file=signed_child, tx_raw_output=child)],
)
signed_parent = cluster.g_transaction.sign_tx(
    tx_body_file=parent.out_file,
    tx_name="batch",
    signing_key_files=parent_signing_keys,
)
cluster.g_transaction.submit_tx(tx_file=signed_parent, txins=parent.txins)
```

`calculate_tx_fee` and `send_tx` also accept `sub_transactions`. Each `SignedSubTx`
must describe its signed file exactly. Supply its explicit net `deposit` when the
child contains certificates or proposals; use negative amounts for refunds.
Fees belong to the parent, and fee estimation must use the complete embedded body.
Embedded witnesses are already included, so witness counts describe additional
parent witnesses only. Reference-script sizes must cover the whole batch.

For imported files without build details, use `build_raw_tx(sub_transaction_files=[...])`:

```python
parent = cluster.g_transaction.build_raw_tx(
    src_address=fee_address,
    tx_name="manual_batch",
    txins=parent_inputs,
    txouts=manually_balanced_parent_outputs,
    fee=parent_fee,
    sub_transaction_files=[signed_child],
)
```

This mode uses your explicit inputs and outputs without selecting inputs or adding
change. You must balance the whole batch, not just the parent. Negative output
amounts, including the -1 sentinel, are rejected. `src_address`, `src_addr_utxos`,
and `deposit` do not affect balancing in this mode. Do not combine
`sub_transaction_files` with the automatically balanced `sub_transactions` option.
`build_raw_tx_bare(signed_sub_tx_files=[...])` also accepts imported files.

The CLI's `build` and `build-estimate` commands do not support embedding yet. Once
they do, their library wrappers can pass signed files directly to the CLI for
automatic batch balancing without requiring `SignedSubTx` build details.

Sub-transactions have no fee, collateral, or script-validity flag. Use the parent's
`collateral_txins`, `return_collateral_txouts`, and `total_collateral_amount` for
Plutus batches. Executed Plutus scripts must be V4; reference witnesses must set
`reference_type=clusterlib.ScriptTypes.PLUTUS_V4` explicitly. Script records with
collateral are rejected when building a child. `protocol_params_file` allows
offline child building; otherwise required parameters are obtained from the node.

`TxGuard` represents a transaction guard, independent of whether the transaction
is top-level or a sub-transaction. Normal transaction builders will expose guards
once the CLI supports them there.

`RequiredTopLevelGuard` records requirements on the enclosing transaction, not local
witnesses. Key requirements can be satisfied with the parent's required signers
and signatures. A current CLI issue prevents general guard support on normal
transactions; those guards will be available once it is fixed.
Local Plutus guards use redeemers and execution units; top-level Plutus
requirements use datums. The CLI validates script-file languages and data rules.

Only unsigned children can be signed, including with zero keys. Incremental
signing and Byron witnesses are unsupported. Set `out_canonical_cbor=True` when
building if canonical encoding is needed, before signing. Do not alter signed
children. Use `g_sub_transaction.get_txid(sub_tx_file=child.out_file)` or
`get_txid(signed_sub_tx_file=signed_child)` for their stable IDs. Query child outputs
with `g_query.get_utxo(txin=f"{child_id}#0")`, not the parent's transaction ID.

### More examples

See [cardano-node-tests](https://github.com/input-output-hk/cardano-node-tests) for more examples, e.g. [minting new tokens](https://github.com/input-output-hk/cardano-node-tests/blob/4b50e8069f5294aaba14140ef0509e2857bec35d/cardano_node_tests/utils/clusterlib_utils.py#L491) or [minting new tokens with Plutus](https://github.com/input-output-hk/cardano-node-tests/blob/4b50e8069f5294aaba14140ef0509e2857bec35d/cardano_node_tests/tests/tests_plutus/test_mint_build.py#L151-L195)


## Source Documentation

<https://cardano-clusterlib-py.readthedocs.io/en/latest/cardano_clusterlib.html>


## Contributing

Install this package and its dependencies as described above.

Run `pre-commit install` to set up the git hook scripts that will check you changes before every commit. Alternatively run `make lint` manually before pushing your changes.

Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), with the exception that formatting is handled automatically by [Ruff](https://github.com/astral-sh/ruff) (through `pre-commit` command).
