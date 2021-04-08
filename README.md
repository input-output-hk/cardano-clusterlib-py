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

# specify where to send funds and amounts to send
destinations = [clusterlib.TxOut(address=dst_address, amount=amount_lovelace)]

# provide keys needed for signing the transaction
tx_files = clusterlib.TxFiles(signing_key_files=[src_skey_file])

# build, sign and submit the transaction
tx_raw_output = cluster.send_funds(
    src_address=src_address,
    destinations=destinations,
    tx_name="send_funds",
    tx_files=tx_files,
)

# wait for two new blocks to make sure the transaction is on the ledger
cluster.wait_for_new_block(new_blocks=2)

# check that the funds were received
cluster.get_utxo(dst_address)
```

See [cardano-node-tests](https://github.com/input-output-hk/cardano-node-tests) for more examples, e.g. [minting new tokens](https://github.com/input-output-hk/cardano-node-tests/blob/6da4cf210bc1da9f1304e67e226063772fff631d/cardano_node_tests/utils/clusterlib_utils.py#L495-L543).


Source Documentation
--------------------

<https://cardano-clusterlib-py.readthedocs.io/en/latest/cardano_clusterlib.html>


Contributing
------------

Install this package and its dependencies as described above.

Run `pre-commit install` to set up the git hook scripts that will check you changes before every commit. Alternatively run `make lint` manually before pushing your changes.

Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), with the exception that formatting is handled automatically by [Black](https://github.com/psf/black) (through `pre-commit` command).
