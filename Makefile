.PHONY: build

.docs_build_dir:
	mkdir -p docs/build

install:
	python3 -m pip install --upgrade pip
	python3 -m pip install --upgrade wheel
	python3 -m pip install --upgrade -r requirements-dev.txt

.install_doc:
	python3 -m pip install --upgrade -r docs/requirements.txt

# run linters
lint:
	pre-commit run -a

build:
	python setup.py -q sdist bdist_wheel

release: build
	python3 -m pip install --upgrade twine
	twine upload --skip-existing dist/*

# generate sphinx documentation
doc: .docs_build_dir .install_doc
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
