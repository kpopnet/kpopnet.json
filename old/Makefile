all: dev

env:
	python3 -m venv env

dev: env
	env/bin/pip install -e .

clean:
	rm -rf env kpopnet.egg-info
