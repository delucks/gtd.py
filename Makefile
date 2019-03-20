.PHONY : black build test

black:
	black -l 120 -S gtd.py todo/ tests/

build:
	python setup.py bdist bdist_wheel

test:
	python -m pytest tests/

# TODO venv creation & cleanup
