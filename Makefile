.PHONY: help up down logs run seed health test docker-build docker-up docker-logs docker-seed

.DEFAULT_GOAL := help

help:			## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up:			## Start MiniStack (app runs locally: make run)
	docker compose up -d

down:			## Stop MiniStack and the app container
	docker compose --profile app down

logs:			## Tail MiniStack logs
	docker compose logs -f ministack

run:			## Run the FastAPI app locally with uvicorn
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

seed:			## Seed SSM parameters + secrets into MiniStack
	python -m bootstrap.seed

health:			## Check MiniStack + app health
	curl -s localhost:4566/_ministack/health && echo && curl -s localhost:8000/healthz

test:			## Run the test suite (mocked AWS, no MiniStack needed)
	pytest

docker-build:		## Build the app image
	docker compose --profile app build

docker-up:		## Start MiniStack + the app, both in Docker
	docker compose --profile app up -d --build

docker-logs:		## Tail the app container logs
	docker compose logs -f app

docker-seed:		## Seed MiniStack from inside the app container
	docker compose --profile app run --rm app python -m bootstrap.seed

docker-down:		## Stop MiniStack + the app container
	docker compose --profile app down
