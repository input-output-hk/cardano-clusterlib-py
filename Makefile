install:
	python3 -m pip install --upgrade pip
	python3 -m pip install --upgrade wheel
	python3 -m pip install --upgrade -r requirements-dev.txt

# run linters
lint:
	pre-commit run -a
