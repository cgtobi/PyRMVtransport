.PHONY: clean coverage beta test lint typing
coverage:
	py.test --verbose --cov-report term-missing --cov-report xml --cov=RMVtransport tests
build:
	python3 setup.py sdist bdist_wheel
clean:
	rm -rf dist/ build/ .egg PyRMVtransport.egg-info/
publish: build
	twine upload dist/*
	rm -rf dist/ build/ .egg PyRMVtransport.egg-info/
beta: build
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*
	rm -rf dist/ build/ .egg PyRMVtransport.egg-info/
test:
	py.test tests
lint:
	flake8 RMVtransport
	pylint --rcfile=.pylintrc RMVtransport
typing:
	mypy RMVtransport
