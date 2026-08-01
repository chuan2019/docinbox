.PHONY: help up down logs run seed health test

.DEFAULT_GOAL := help

help:		## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

up:			## Start MiniStack
	docker compose up -d

down:		## Stop MiniStack
	docker compose down

logs:		## Tail MiniStack logs
	docker compose logs -f minstack

run:		## Run the FastAPI app
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

seed:		## Seed SSM parameters + secrets into MiniStack
	python -m bootstrap.seed

health:		## Check MiniStack + app health
	curl -s localhost:4566/_ministack/health && echo && curl -s localhost:8000/healthz

test:		## Run the test suite (mocked AWS, no MiniStack needed)
	pytest

