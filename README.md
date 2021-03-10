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

cluster = clusterlib.ClusterLib(state_dir="path/to/cluster/state_dir")

destinations = [clusterlib.TxOut(address=dst_address, amount=amount_lovelace)]
tx_files = clusterlib.TxFiles(signing_key_files=[src_skey_file])

tx_raw_output = cluster.send_funds(
    src_address=src_address,
    destinations=destinations,
    tx_name="send_funds",
    tx_files=tx_files,
)
cluster.wait_for_new_block(new_blocks=2)

cluster.get_utxo(src_address)
```

See [cardano-node-tests](https://github.com/input-output-hk/cardano-node-tests) for more examples.


Contributing
------------

Install this package and its dependencies as described above.

Run `pre-commit install` to set up the git hook scripts that will check you changes before every commit. Alternatively run `make lint` manually before pushing your changes.

Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), with the exception that formatting is handled automatically by [Black](https://github.com/psf/black) (through `pre-commit` command).
