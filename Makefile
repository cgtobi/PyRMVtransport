.PHONY: clean coverage beta test lint typing
init:
	pip install flit
	flit install
	pre-commit install
coverage:
	py.test --verbose --cov-report term-missing --cov-report xml --cov=RMVtransport tests
build:
	flit build
clean:
	rm -rf dist/
publish:
	flit --repository pypi publish
beta:
	flit --repository testpypi publish
test:
	py.test tests
lint:
	flake8 RMVtransport
	pylint --rcfile=.pylintrc RMVtransport
typing:
	mypy RMVtransport
all: test lint typing
