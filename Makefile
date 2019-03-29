.PHONY: clean coverage beta test lint typing
coverage:
	py.test --verbose --cov-report term-missing --cov-report xml --cov=RMVtransport tests
build:
	flit build
clean:
	rm -rf dist/ build/ .egg PyRMVtransport.egg-info/
publish: build
	flit --repository pypi publish
	rm -rf dist/ build/ .egg PyRMVtransport.egg-info/
beta: build
	flit --repository testpypi publish
	rm -rf dist/ build/ .egg PyRMVtransport.egg-info/
test:
	py.test tests
lint:
	flake8 RMVtransport
	pylint --rcfile=.pylintrc RMVtransport
typing:
	mypy RMVtransport
