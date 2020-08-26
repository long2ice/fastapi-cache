checkfiles = fastapi_cache/ examples/ tests/
black_opts = -l 100 -t py38
py_warn = PYTHONDEVMODE=1

help:
	@echo "FastAPI-Cache development makefile"
	@echo
	@echo  "usage: make <target>"
	@echo  "Targets:"
	@echo  "    up			Ensure dev/test dependencies are updated"
	@echo  "    deps		Ensure dev/test dependencies are installed"
	@echo  "    check		Checks that build is sane"
	@echo  "    test		Runs all tests"
	@echo  "    style		Auto-formats the code"
	@echo  "    build		Build package"

up:
	@poetry update

deps:
	@poetry install --no-root -E all

style: deps
	@isort -src $(checkfiles)
	@black $(black_opts) $(checkfiles)

check: deps
	@black --check $(black_opts) $(checkfiles) || (echo "Please run 'make style' to auto-fix style issues" && false)
	@flake8 $(checkfiles)
	@bandit -r $(checkfiles)

test: deps
	$(py_warn) pytest

build: deps
	@poetry build

ci: check test
