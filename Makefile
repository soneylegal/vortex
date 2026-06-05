.PHONY: install test lint format run ingest ci docker clean docker-lint docker-format docker-typecheck docker-test docker-ci docs docker-docs

# ── Development ─────────────────────────────────────────────────────────

install:
	pip install -e ".[dev]"

run:
	uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload

ingest:
	python scripts/ingest_data.py

ingest-clean:
	python scripts/ingest_data.py --clear

# ── Quality ─────────────────────────────────────────────────────────────

lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .

typecheck:
	mypy src/ --ignore-missing-imports

test:
	pytest tests/ -v

ci: lint typecheck test
	@echo "✓ All CI checks passed."

# ── Docker ──────────────────────────────────────────────────────────────

docker:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

docker-lint:
	docker compose run --rm api ruff check .

docker-format:
	docker compose run --rm api ruff format .
	docker compose run --rm api ruff check --fix .

docker-typecheck:
	docker compose run --rm api mypy src/ --ignore-missing-imports

docker-test:
	docker compose run --rm api pytest tests/ -v

docker-ci: docker-lint docker-typecheck docker-test
	@echo "✓ All Docker CI checks passed."

# ── Documentation ───────────────────────────────────────────────────────

docs:
	mkdocs serve

docker-docs:
	docker compose run --rm -p 8001:8001 api mkdocs serve -a 0.0.0.0:8001

# ── Cleanup ─────────────────────────────────────────────────────────────

clean:
	rm -rf data/chroma_db/
	rm -rf .ruff_cache/ .mypy_cache/ .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
