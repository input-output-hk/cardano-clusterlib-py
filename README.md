# README for cardano-clusterlib

[![Documentation Status](https://readthedocs.org/projects/cardano-clusterlib-py/badge/?version=latest)](https://cardano-clusterlib-py.readthedocs.io/en/latest/?badge=latest)
[![PyPi Version](https://img.shields.io/pypi/v/cardano-clusterlib.svg)](https://pypi.org/project/cardano-clusterlib/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

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

On custom testnets that were started in Byron era, you might need to specify a slots offset between Byron epochs and Shelley epochs.
The "slots_offset" is a difference between number of slots in Byron epochs and in the same number of Shelley epochs.

E.g. for a testnet with parameters

* 100 slots per epoch in Byron era
* 1000 slots per epoch in Shelley era
* two epochs in Byron era before forking to Shelley

The offset will be `2 * (1000 - 100) = 1800`.

```python
cluster = clusterlib.ClusterLib(state_dir="path/to/cluster/state_dir", slots_offset=1800)
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
cluster = clusterlib.ClusterLib(state_dir="path/to/cluster/state_dir", tx_era="babbage")

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

### More examples

See [cardano-node-tests](https://github.com/input-output-hk/cardano-node-tests) for more examples, e.g. [minting new tokens](https://github.com/input-output-hk/cardano-node-tests/blob/4b50e8069f5294aaba14140ef0509e2857bec35d/cardano_node_tests/utils/clusterlib_utils.py#L491) or [minting new tokens with Plutus](https://github.com/input-output-hk/cardano-node-tests/blob/4b50e8069f5294aaba14140ef0509e2857bec35d/cardano_node_tests/tests/tests_plutus/test_mint_build.py#L151-L195)


## Source Documentation

<https://cardano-clusterlib-py.readthedocs.io/en/latest/cardano_clusterlib.html>


## Contributing

Install this package and its dependencies as described above.

Run `pre-commit install` to set up the git hook scripts that will check you changes before every commit. Alternatively run `make lint` manually before pushing your changes.

Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), with the exception that formatting is handled automatically by [Black](https://github.com/psf/black) (through `pre-commit` command).
