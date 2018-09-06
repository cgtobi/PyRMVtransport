.PHONY: ci coverage flake8 init publish clean test
ci:
	pipenv run py.test --junitxml=report.xml
coverage:
	pipenv run py.test --verbose --cov-report term-missing --cov-report xml --cov=RMVtransport tests
flake8:
	pipenv run flake8 RMVtransport
init:
	pip install --upgrade pip pipenv
	pipenv lock
	pipenv install --dev
publish:
	python3 setup.py sdist bdist_wheel
	pipenv run twine upload dist/*
	clean
clean:
	rm -rf dist/ build/ .egg PyRMVtransport.egg-info/
test:
	pipenv run detox
