[![Documentation Status](https://readthedocs.org/projects/cardano-clusterlib-py/badge/?version=latest)](https://cardano-clusterlib-py.readthedocs.io/en/latest/?badge=latest)
[![PyPi Version](https://img.shields.io/pypi/v/cardano-clusterlib.svg)](https://pypi.org/project/cardano-clusterlib/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

README for cardano-clusterlib
=============================

Python wrapper for cardano-cli for working with cardano cluster.

Installation
------------

```sh
# create and activate virtual env
$ python3 -m venv .env
$ . .env/bin/activate
# install it from PyPI
$ pip install cardano-clusterlib
# - OR - install it in develop mode together with dev requirements
$ make install
```

Usage
-----

Needs working `cardano-cli` (the command is available on `PATH`, `cardano-node` is running, `CARDANO_NODE_SOCKET_PATH` is set). In `state_dir` it expects "shelley/genesis.json".

```python
from cardano_clusterlib import clusterlib

# instantiate `ClusterLib`
cluster = clusterlib.ClusterLib(state_dir="path/to/cluster/state_dir")

src_address = "addr_test1vpst87uzwafqkxumyf446zr2jsyn44cfpu9fe8yqanyuh6glj2hkl"
src_skey_file = "/path/to/skey"

dst_addr = cluster.gen_payment_addr_and_keys(name="destination_address")
amount_lovelace = 10_000_000  # 10 ADA

# specify where to send funds and amounts to send
txouts = [clusterlib.TxOut(address=dst_addr.address, amount=amount_lovelace)]

# provide keys needed for signing the transaction
tx_files = clusterlib.TxFiles(signing_key_files=[src_skey_file])

# build, sign and submit the transaction
tx_raw_output = cluster.send_tx(
    src_address=src_address,
    tx_name="send_funds",
    txouts=txouts,
    tx_files=tx_files,
)

# check that the funds were received
cluster.get_utxo(dst_addr.address)
```

See [cardano-node-tests](https://github.com/input-output-hk/cardano-node-tests) for more examples, e.g. [minting new tokens](https://github.com/input-output-hk/cardano-node-tests/blob/90aa4a2e9fe4019a89e6f4cdec7cb092732e6f2a/cardano_node_tests/utils/clusterlib_utils.py#L567-L602) or [minting new tokens with Plutus](https://github.com/input-output-hk/cardano-node-tests/blob/d688a9bcf00a30f9881c52aab9311dd1a0cb3077/cardano_node_tests/tests/test_plutus_mint_build.py#L173-L217)


Source Documentation
--------------------

<https://cardano-clusterlib-py.readthedocs.io/en/latest/cardano_clusterlib.html>


Contributing
------------

Install this package and its dependencies as described above.

Run `pre-commit install` to set up the git hook scripts that will check you changes before every commit. Alternatively run `make lint` manually before pushing your changes.

Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), with the exception that formatting is handled automatically by [Black](https://github.com/psf/black) (through `pre-commit` command).
