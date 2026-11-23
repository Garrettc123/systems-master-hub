.PHONY: install test compile ci e2e backup compose-config preflight
install:
	python -m pip install -e ".[dev]"
test:
	python -m pytest -q
compile:
	python -m compileall -q app tests
ci:
	./scripts/ci.sh
e2e:
	./scripts/e2e-smoke.sh
backup:
	python -m app.backup create
compose-config:
	docker compose config --quiet
preflight:
	./scripts/preflight.sh
