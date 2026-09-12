.PHONY: install run test test-integration lint docker-build docker-run

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --port $${PORT:-8000}

test:
	pytest

test-integration:
	RUN_INTEGRATION_TESTS=1 pytest tests/integration -v

lint:
	pip install ruff --quiet
	ruff check app tests

docker-build:
	docker build -t github-issues-gateway .

docker-run:
	docker run --rm -it --env-file .env -p $${PORT:-8000}:$${PORT:-8000} github-issues-gateway
