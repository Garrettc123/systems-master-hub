.PHONY: install test lint preflight compose-config

install:
	python -m pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check app tests

preflight:
	./scripts/preflight.sh

compose-config:
	docker compose config --quiet
