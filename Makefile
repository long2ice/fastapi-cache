checkfiles = fastapi_cache/ examples/ tests/
py_warn = PYTHONDEVMODE=1

up:
	@poetry update

deps:
	@poetry install --no-root -E all

style: deps
	@poetry run isort -src $(checkfiles)
	@poetry run black $(checkfiles)

check: deps
	@poetry run black $(checkfiles) || (echo "Please run 'make style' to auto-fix style issues" && false)
	@poetry run flake8 $(checkfiles)
	@poetry run bandit -r $(checkfiles)

test: deps
	$(py_warn) poetry run pytest

build: clean deps
	@poetry build

clean:
	@rm -rf ./dist

ci: check test
