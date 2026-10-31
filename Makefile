.PHONY: db run worker reset-db demo test lint api-types

PYTHON = backend/.venv/bin/python

db:            ## start the database in Docker
	docker compose up -d db

run:           ## start the backend at http://localhost:8000 (uvicorn, so live updates can stream)
	cd backend && .venv/bin/uvicorn config.asgi:application --reload --port 8000

worker:        ## background jobs: Celery worker + timer. --pool=solo suits macOS; on a Linux server drop it
	cd backend && .venv/bin/celery -A config worker --beat --pool=solo -l info

reset-db:      ## empty the database and recreate all tables (development only)
	cd backend && .venv/bin/python manage.py reset_database
	cd backend && .venv/bin/python manage.py migrate

demo:          ## fill the database with the Aarav & Meera demo wedding
	cd backend && .venv/bin/python manage.py load_demo_data

test:          ## run the backend tests
	cd backend && .venv/bin/python manage.py test

lint:          ## check the backend code style
	cd backend && .venv/bin/ruff check .

api-types:     ## refresh the frontend's API types (backend must be running)
	cd frontend && npm run api-types
