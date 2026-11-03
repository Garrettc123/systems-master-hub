PYTHON ?= python3
.PHONY: ci test smoke

ci:
	$(PYTHON) scripts/ci.py

test:
	$(PYTHON) -m unittest discover -s tests -v

smoke:
	$(PYTHON) -m garcar_actions.smoke
