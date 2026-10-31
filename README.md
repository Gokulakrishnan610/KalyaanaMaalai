# KalyaanaMaalai

Wedding planning system for Shaandaar Events: from the first couple enquiry to vendor payments and the final profit.

**Backend:** Django + Django REST Framework + PostgreSQL. **Website:** React (Vite + TypeScript + Tailwind).

## Run it on your machine

You need Python 3.10+, Node 20+ and PostgreSQL 15 (Docker or installed locally).

```bash
# 1. settings files
cp .env.example .env
cp frontend/.env.example frontend/.env.local

# 2. database and Redis: use Docker...
docker compose up -d db redis
# ...or a local Postgres (user "wedding", password "wedding", database "wedding"; the user also
#    needs CREATEDB so the tests can run) and a local Redis (`brew install redis && brew services start redis`)

# 3. backend
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
make reset-db        # creates all the tables
make demo            # loads the Aarav & Meera demo data
make run             # backend at http://localhost:8000 (uvicorn: live updates need it)

# 4. background jobs (second terminal): late-vendor alerts, payment reminders, Telegram
make worker

# 5. website (third terminal)
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
  incidents/        problems reported during weddings: assign, track, resolve
  live/             instant updates: events go through Redis to every open browser
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
| `make worker` | Run the Celery worker and timer (needs Redis) |
| `make api-types` | Refresh the website's API types (backend must be running) |

When you change a model: `cd backend && .venv/bin/python manage.py makemigrations`, commit the new migration file, and teammates run `make reset-db && make demo` or `manage.py migrate`.

## What works today (Member 1 part)

- **Login** for founder, planner and staff, with role checks (staff can look but not change; only the founder deletes).
- **Enquiries:** board (drag a card to change its stage) and table, filter by source, search, add/edit form, first-consultation date, and **Convert to client** (optionally also starting the wedding project). Converting twice never creates a second client.
- **Odoo-style CRM fields:** each enquiry has an expected fee, chance of winning (starts from the stage: New 10%, Contacted 20%, Consultation 40%, Proposal 60%, Won 100%, Lost 0%, and can be edited), priority stars, expected decision date, and a required reason when it is lost. Dragging a card to Lost asks for the reason.
- **Follow-ups (Odoo activities):** plan calls, meetings, WhatsApp messages, emails or to-dos on an enquiry, tick them off, and see overdue ones in red on the table and the dashboard.
- **Clients:** list, search, and a profile showing weddings, enquiry history and what the couple still owes.
- **Dashboard:** revenue, expenses, profit, money couples still owe, enquiries by source, profit per wedding, vendor payments due this week, upcoming consultations and a late-vendors alert.

The dashboard reads the weddings, payments, tasks and vendor-arrival tables, so it fills up automatically as the other members' parts are built.

## What works today (Member 4 part: money, AI and alerts)

- **Finance tab** (`FinanceTab` in `frontend/src/pages/payments`, also the **Payments** page): revenue, expenses, estimated and actual profit, margin, budget charts, client invoices, vendor bills, advance/final instalments and the vendor payments due soon (overdue in red). Member 2: drop `<FinanceTab weddingId={wedding.id} />` into the wedding page.
- **Invoices and payments:** a deposit, instalments, extra-guest charges (guests above the contract x the per-guest rate) and a final invoice. An invoice's status (unpaid / part paid / paid) is worked out from its payments. Paying more than is left is refused (409).
- **Vendor bills:** the same vendor + bill reference twice is refused, and a bill with the same vendor and amount due within a week gives a warning. Vendor payments send an `Idempotency-Key`, so a double click or retry records one payment.
- **Pay online (Razorpay test mode):** "Pay online" on an invoice. With `MOCK_EXTERNALS=true` it opens a demo checkout and no real money moves.
- **AI:** `POST /api/ai/extract-quotation/` reads a vendor PDF or photo and returns a draft in paise (the form can edit it before saving); `POST /api/ai/generate-checklist/` previews 25-40 tasks tailored to the wedding and `.../confirm/` saves the ones you keep. If AI is off or fails, a built-in checklist is used. Components: `AIExtractModal` and `AIChecklistButton` in `frontend/src/pages/ai`.
- **Alerts:** the bell in the top bar (refreshes every 30 s) and the Notifications page. `notifications.services.notify(message, severity=...)` saves an alert and sends it to Telegram when set up. `make worker` also reminds you once a day about vendor payments due within 3 days or overdue.

### Set up Telegram alerts (optional)

1. In Telegram, message **@BotFather**, send `/newbot` and follow the steps. Copy the **token** it gives you.
2. Open a chat with your new bot (or add it to a group) and send any message.
3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and copy the number at `"chat":{"id": ...}`.
4. In `.env` set `TELEGRAM_BOT_TOKEN=...`, `TELEGRAM_CHAT_ID=...` and `MOCK_EXTERNALS=false`, then restart the backend.

While `MOCK_EXTERNALS=true` alerts only appear in the bell (and the server log).

### Set up Razorpay test payments (optional)

1. Create a free account at razorpay.com and switch the dashboard to **Test Mode**.
2. Open Settings -> API Keys -> Generate Test Key. Put the two values in `.env` as `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`, set `MOCK_EXTERNALS=false`, restart.
3. In the test checkout use card `4111 1111 1111 1111` with any future expiry and any CVV, or UPI `success@razorpay`. "Record payment" always works as a manual fallback.

### Set up AI (optional)

Put `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`, default `gpt-4o-mini`) in `.env` and set `MOCK_EXTERNALS=false`. Amounts are always converted to paise in our own code, and the totals are cross-checked against the line items.

## Putting it online (not tested yet)

Backend (Render, Railway or similar), with a hosted Postgres:

```bash
pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput   # build
uvicorn config.asgi:application --host 0.0.0.0 --port $PORT --workers 2                                    # start (not gunicorn's plain workers: they would block live updates)
celery -A config worker --beat -l info                                                                     # second process: background jobs
python manage.py load_demo_data                                                                            # once, for demo data
```

Set these environment variables: `ENVIRONMENT=production`, `SECRET_KEY` (long and random), `DATABASE_URL`, `ALLOWED_HOSTS` (your backend's domain), `FRONTEND_URL` (your website's address), `REDIS_URL` (a hosted Redis, for example Render Key Value or Upstash), `MOCK_EXTERNALS=true`. Run exactly **one** Celery process with `--beat`, otherwise every timed job runs twice.

Website (Vercel or Netlify): build command `npm run build`, folder `frontend`, output `dist`, environment variable `VITE_API_URL=https://your-backend-domain/api`.

## Live updates (no refreshing)

Open screens update by themselves. When anything changes, the backend publishes a small event to **Redis**, and every logged-in browser receives it over one open connection (**Server-Sent Events**, `GET /api/live/stream/`). The website then refreshes just the screens that event affects, and alerts appear as pop-ups. A green **Live** dot in the top bar shows the connection. If it drops, the website reconnects and catches up on what it missed.

| What happens | Who sees it, instantly |
|---|---|
| A task moves or is assigned | Everyone's task board and the dashboard; the assignee also gets an alert |
| A vendor checks in or is marked late | Event Day screen, wedding page, dashboard; planners get a late alert |
| An incident is reported | All planners get an alert (serious ones also go to Telegram); the incidents list and dashboard update |
| A vendor sends a quotation | Planners get an alert; the comparison table updates |
| A payment is recorded | Planners get an alert; the finance tab, the client's balance and the dashboard update |

How it works: `live/signals.py` listens for saves (tasks, arrivals, payments, quotations, incidents, alerts) and publishes events after the database commit, so no other app has to call anything. `live/bus.py` is the Redis connection (publishing takes a millisecond and never fails a save if Redis is down). `live/views.py` is the stream. `frontend/src/live/` reads it. To make something else live, add one handler in `live/signals.py` and list which screens to refresh in `frontend/src/live/LiveProvider.tsx`.

## Background jobs (Celery + Redis)

Timed and slow work runs outside the web request, in a **Celery** worker with Redis as the message queue (`make worker`). The schedule comes from `backend/common/jobs.py`: late-vendor check every minute, vendor payment reminders every morning. Telegram messages are also sent by the worker, so raising an alert never waits on Telegram; if the worker is down, it is sent directly instead.

## Rules we agreed on

- **Money** is always whole **paise** (1 rupee = 100 paise). The website converts for display.
- **Roles:** founder (everything), planner, staff. The founder passes every permission check. Use `allow_roles(Role.PLANNER)` from `common/permissions.py`.
- **Outside services** (AI, Razorpay, Telegram, email) give fake answers while `MOCK_EXTERNALS=true`, so demos never break.
- **Timed jobs:** write a function in your app and add one line to `backend/common/jobs.py`. Celery runs it (`make worker`).
- Only Member 1 edits `backend/config/urls.py`, `frontend/src/App.tsx` and the layout. Everyone else works inside their own app folder and page folder.

## Branches and commits

Branches: `feature/member1-core`, `feature/member2-weddings`, `feature/member3-vendors`, `feature/member4-finance-ai`. Open a pull request to `main`, never push to it directly. Keep commits meaningful and fairly large: one commit per finished piece of work, with a clear sentence describing it.
