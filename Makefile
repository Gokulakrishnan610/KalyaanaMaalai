.PHONY: db run reset-db demo test lint jobs api-types

PYTHON = backend/.venv/bin/python

db:            ## start the database in Docker
	docker compose up -d db

run:           ## start the backend at http://localhost:8000
	cd backend && .venv/bin/python manage.py runserver 8000

reset-db:      ## empty the database and recreate all tables (development only)
	cd backend && .venv/bin/python manage.py reset_database
	cd backend && .venv/bin/python manage.py migrate

demo:          ## fill the database with the Aarav & Meera demo wedding
	cd backend && .venv/bin/python manage.py load_demo_data

test:          ## run the backend tests
	cd backend && .venv/bin/python manage.py test

lint:          ## check the backend code style
	cd backend && .venv/bin/ruff check .

jobs:          ## run timed background jobs (late-vendor alerts, payment reminders)
	cd backend && .venv/bin/python manage.py run_jobs

api-types:     ## refresh the frontend's API types (backend must be running)
	cd frontend && npm run api-types
