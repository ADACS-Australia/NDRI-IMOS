.PHONY: build

build:
	python3 -m build

install: build
	python3 -m pip install .

clean:
	python3 -m pip -v uninstall IMOSPATools
	python3 -m pip -v cache purge

force: clean
	make install


