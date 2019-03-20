.PHONY : black build test clean

black:
	black -l 120 -S gtd.py todo/ tests/

build:
	python setup.py bdist bdist_wheel

venv: venv/bin/activate

venv/bin/activate: requirements.txt
	test -d venv || virtualenv venv
	. venv/bin/activate; pip install -Ur requirements.txt
	touch venv/bin/activate

test: venv
	. venv/bin/activate; python -m pytest tests/

clean:
	rm -rf venv
	find -iname "*.pyc" -delete
