.PHONY: install
# TODO: for pylint and mypy, see https://github.com/PyCQA/pylint/issues/7306
install: export SETUPTOOLS_ENABLE_FEATURES="legacy-editable"
install:
	python3 -m pip install --upgrade pip
	python3 -m pip install --upgrade wheel
	python3 -m pip install --upgrade --upgrade-strategy eager -r requirements-dev.txt $(PIP_INSTALL_ARGS)
	virtualenv --upgrade-embed-wheels

.PHONY: .install_doc
# TODO: for pylint and mypy, see https://github.com/PyCQA/pylint/issues/7306
.install_doc: export SETUPTOOLS_ENABLE_FEATURES="legacy-editable"
.install_doc:
	python3 -m pip install --upgrade --upgrade-strategy eager -r docs/requirements.txt

# run linters
.PHONY: lint
lint:
	pre-commit run -a
	if type pytype >/dev/null 2>&1; then pytype cardano_clusterlib; fi

# build package
.PHONY: build
build:
	python -c "import build" || python3 -m pip install build
	python3 -m build

# upload package to PyPI
.PHONY: upload
upload:
	if ! type twine >/dev/null 2>&1; then python3 -m pip install --upgrade twine; fi
	twine upload --skip-existing dist/*

# release package to PyPI
.PHONY: release
release: build upload

.PHONY: .docs_build_dir
.docs_build_dir:
	mkdir -p docs/build

# generate sphinx documentation
.PHONY: doc
doc: .docs_build_dir .install_doc
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
