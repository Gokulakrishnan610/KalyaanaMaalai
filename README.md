# KalyaanaMaalai

Wedding planning system for Shaandaar Events: from the first couple enquiry to vendor payments and the final profit.

**Backend:** Django + Django REST Framework + PostgreSQL. **Website:** React (Vite + TypeScript + Tailwind).

## Run it on your machine

You need Python 3.10+, Node 20+ and PostgreSQL 15 (Docker or installed locally).

```bash
# 1. settings files
cp .env.example .env
cp frontend/.env.example frontend/.env.local

# 2. database: use Docker...
docker compose up -d db
# ...or a local Postgres with user "wedding", password "wedding", database "wedding"
#    (the user also needs CREATEDB so the tests can run)

# 3. backend
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
make reset-db        # creates all the tables
make demo            # loads the Aarav & Meera demo data
make run             # backend at http://localhost:8000

# 4. website (second terminal)
cd frontend && npm install && npm run dev    # http://localhost:5173
```

Demo logins (password `Demo@12345`): `founder@shaandaar.demo`, `planner@shaandaar.demo`, `staff@shaandaar.demo`.

Handy pages while developing:
- `http://localhost:8000/admin/` – see and edit every table (log in as the founder)
- `http://localhost:8000/api/docs/` – every API endpoint, with a "Try it out" button

## What is in each folder

```
backend/
  config/           project settings and the main list of web addresses
  accounts/         users and login
  clients/          the couples we work for
  enquiries/        first contact: calls, Instagram, WhatsApp
  weddings/         weddings, their functions (Mehendi, Sangeet...), run sheet, vendor arrival
  tasks/            the to-do board for each wedding
  vendors/          caterers, decorators, DJs and their details
  quotations/       asking vendors for prices, comparing, picking the winner
  payments/         what couples pay us, what we pay vendors, profit
  ai_tools/         reading quotation PDFs and writing checklists with AI
  notifications/    alerts (bell icon, Telegram)
  dashboard/        the founder's summary page
  common/           shared helpers: who-can-do-what, timed jobs, demo-data command
  demo_data/        the sample wedding used for demos

frontend/src/
  pages/            one folder per screen (login, dashboard, enquiries, weddings, ...)
  components/       buttons, tables, forms (common/) and the login guard
  layout/           the sidebar and top bar
  login/            who is logged in
  api/              how the website talks to the backend
  helpers/          money (paise to rupees) and date formatting
  types/            API types, made automatically from the backend
```

Every backend folder follows the same pattern: `models.py` (the data), `serializers.py` (what the API sends and accepts), `views.py` (the logic), `urls.py` (the web addresses), `admin.py` (the admin pages), `tests.py`.

## Everyday commands

| Command | What it does |
|---|---|
| `make run` | Start the backend |
| `make reset-db` | Empty the database and rebuild the tables (development only) |
| `make demo` | Load the demo wedding (safe to run twice) |
| `make test` | Run the backend tests |
| `make jobs` | Run timed jobs, like late-vendor alerts |
| `make api-types` | Refresh the website's API types (backend must be running) |

When you change a model: `cd backend && .venv/bin/python manage.py makemigrations`, commit the new migration file, and teammates run `make reset-db && make demo` or `manage.py migrate`.

## Rules we agreed on

- **Money** is always whole **paise** (1 rupee = 100 paise). The website converts for display.
- **Roles:** founder (everything), planner, staff. The founder passes every permission check. Use `allow_roles(Role.PLANNER)` from `common/permissions.py`.
- **Outside services** (AI, Razorpay, Telegram, email) give fake answers while `MOCK_EXTERNALS=true`, so demos never break.
- **Timed jobs:** write a function in your app and add one line to `backend/common/jobs.py`.
- Only Member 1 edits `backend/config/urls.py`, `frontend/src/App.tsx` and the layout. Everyone else works inside their own app folder and page folder.

## Branches and commits

Branches: `feature/member1-core`, `feature/member2-weddings`, `feature/member3-vendors`, `feature/member4-finance-ai`. Open a pull request to `main`, never push to it directly. Keep commits meaningful and fairly large: one commit per finished piece of work, with a clear sentence describing it.
