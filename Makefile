.PHONY: build

build:
	python3 -m build

install: build
	python3 -m pip install .
