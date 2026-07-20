.PHONY: up down logs run health test

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

