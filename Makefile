checkfiles = fastapi_cache/ examples/ tests/
py_warn = PYTHONDEVMODE=1

up:
	@poetry update

deps:
	@poetry install --no-root -E all

style: deps
	@isort -src $(checkfiles)
	@black $(checkfiles)

check: deps
	@black $(checkfiles) || (echo "Please run 'make style' to auto-fix style issues" && false)
	@flake8 $(checkfiles)
	@mypy ${checkfiles}
	@pyright ${checkfiles}

test: deps
	$(py_warn) pytest

build: clean deps
	@poetry build

clean:
	@rm -rf ./dist

ci: check test
