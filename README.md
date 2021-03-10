README for cardano-clusterlib
=============================

Python wrapper for cardano-cli for working with cardano cluster.

Installation
------------

```sh
# create and activate virtual env
$ python3 -m venv .env
$ . .env/bin/activate
# install this package together with dev requirements
$ make install
```

Usage
-----

TBD


Contributing
------------

Install this package and its dependencies as described above.

Run `pre-commit install` to set up the git hook scripts that will check you changes before every commit. Alternatively run `make lint` manually before pushing your changes.

Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), with the exception that formatting is handled automatically by [Black](https://github.com/psf/black) (through `pre-commit` command).
