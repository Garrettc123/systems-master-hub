.PHONY: install test compile compose-config preflight
install:
	python -m pip install -e ".[dev]"
test:
	pytest
compile:
	python -m compileall -q app tests
compose-config:
	docker compose config --quiet
preflight:
	./scripts/preflight.sh
