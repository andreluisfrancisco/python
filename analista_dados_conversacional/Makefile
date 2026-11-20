VENV ?= ../.venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
export PYTHONPATH := server

.PHONY: install test init api ui eval up down bootstrap

install:
	$(PIP) install -r requirements.txt -r requirements-dev.txt

test:
	$(PY) -m pytest

bootstrap:
	bash server/scripts/bootstrap_local_postgres.sh

init:
	$(PY) server/scripts/init_db.py

api:
	$(PY) -m uvicorn app.main:app --reload --port 8000

ui:
	$(PY) -m streamlit run client/streamlit_app.py

eval:
	$(PY) -m app.eval.run_eval --mode guard

eval-live:
	$(PY) -m app.eval.run_eval --mode live

up:
	docker compose up --build

down:
	docker compose down
