.PHONY: clean coverage beta test lint typing
coverage:
	pipenv run py.test --verbose --cov-report term-missing --cov-report xml --cov=RMVtransport tests
init:
	pip install --upgrade pip pipenv
	pipenv lock
	pipenv install --dev
build:
	python3 setup.py sdist bdist_wheel
clean:
	rm -rf dist/ build/ .egg PyRMVtransport.egg-info/
publish: build
	pipenv run twine upload dist/*
	rm -rf dist/ build/ .egg PyRMVtransport.egg-info/
beta: build
	pipenv run twine upload --repository-url https://test.pypi.org/legacy/ dist/*
	rm -rf dist/ build/ .egg PyRMVtransport.egg-info/
test:
	pipenv run py.test tests
lint:
	pipenv run flake8 RMVtransport
	pipenv run pylint --rcfile=.pylintrc RMVtransport
typing:
	pipenv run mypy RMVtransport
