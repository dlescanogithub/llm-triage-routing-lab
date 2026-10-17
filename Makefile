PYTHON ?= python3

.PHONY: setup lint format test eval eval-regression secretscan demo live

setup:
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

format:
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .

test:
	$(PYTHON) -m pytest

eval:
	$(PYTHON) -m triage_lab eval

eval-regression:
	$(PYTHON) -m triage_lab eval --regression

secretscan:
	$(PYTHON) -m triage_lab.secretscan

demo:
	$(PYTHON) -m triage_lab demo

live:
	$(PYTHON) -m triage_lab live --split test --max-tickets 40 --models "$${LLM_MODELS}"
