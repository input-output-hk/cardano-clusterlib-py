.PHONY: install
install:
	python3 -m pip install --require-virtualenv --upgrade pip
	python3 -m pip install --require-virtualenv --upgrade -r requirements-dev.txt $(PIP_INSTALL_ARGS)

.PHONY: .install_doc
.install_doc:
	python3 -m pip install --require-virtualenv --upgrade -r docs/requirements.txt

# run linters
.PHONY: lint
lint:
	pre-commit run -a --show-diff-on-failure --color=always
	if command -v pytype >/dev/null 2>&1; then pytype -k -j auto cardano_clusterlib; fi

# build package
.PHONY: build
build:
	python3 -m build

# upload package to PyPI
.PHONY: upload
upload:
	if ! command -v twine >/dev/null 2>&1; then python3 -m pip install --require-virtualenv --upgrade twine; fi
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
