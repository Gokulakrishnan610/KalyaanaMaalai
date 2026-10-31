# KalyaanaMaalai

Wedding planning system for Shaandaar Events: from the first couple enquiry to vendor payments and the final profit, with live updates and online payment links.

**Backend:** Django + Django REST Framework + PostgreSQL + Redis (live updates and background jobs).
**Website:** React (Vite + TypeScript + Tailwind).

## What it does

```
New enquiry -> consultation and follow-ups -> convert to client -> wedding project
   -> ask 3 vendors for quotes -> compare -> pick the winner (bill + instalments created)
   -> invoices: deposit, instalments, extra guests -> collect by payment link or offline
   -> 25+ task plan, run sheet, vendor check-in on the day, incidents
   -> pay vendors -> profit -> founder dashboard
```

| Part | What you can do |
|---|---|
| **Enquiries and clients** | Track enquiries from calls, Instagram and WhatsApp on a board or table. Each has an expected fee, chance of winning (set by stage, editable), priority stars, expected decision date and a required reason if lost. Plan follow-ups (calls, meetings, messages) and see overdue ones in red. Convert to a client, optionally starting the wedding in one step. The client page shows weddings, history and what they still owe. |
| **Weddings and tasks** | A wedding page with tabs: Overview, Functions (Mehendi, Sangeet...), Tasks, Schedule, Vendors, Finance, Event Day, Incidents. A task board (drag between To plan, In progress, Ready, Done), a reusable 25+ task template with owners and due dates, and AI-suggested checklists. |
| **Wedding day** | A minute-by-minute run sheet per function. Each vendor gets a **check-in link** (`/checkin/<code>`): they open it on their phone and tap "I have arrived". A background job flags vendors who are late and alerts planners once. **Incidents** (`/incidents`): anyone can report a problem, planners are alerted at once, assign it, and the assignee resolves it; every step is kept in a history. |
| **Vendors and quotations** | A vendor directory with ratings and punctuality. Ask several vendors of a category for quotes, enter them by hand or let AI read the PDF, compare them side by side (price per plate, line items, best value), and pick the winner. Picking creates the vendor bill with advance and final instalments. |
| **Payments** | See below. |
| **Alerts and dashboard** | The bell in the top bar and Telegram (optional) for alerts. The founder dashboard shows revenue, expenses, profit per wedding, open incidents, follow-ups, vendor payments due, consultations and a live activity feed. |
| **Live updates** | Open screens update by themselves, with no refreshing. See "Live updates" below. |

Roles: **founder** can do everything, **planner** manages weddings and money, **staff** can look, report incidents, add notes and work on tasks assigned to them.

## Run it on your machine

You need Python 3.10+, Node 20+, PostgreSQL 15 and Redis.

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
- `http://localhost:8000/admin/`: see and edit every table (log in as the founder)
- `http://localhost:8000/api/docs/`: every API endpoint, with a "Try it out" button

Pages that need no login (they open from a link): `/pay/<token>` (a customer pays an invoice) and `/checkin/<code>` (a vendor checks in).

## Everyday commands

| Command | What it does |
|---|---|
| `make run` | Start the backend (uvicorn) |
| `make worker` | Run the Celery worker and timer (needs Redis) |
| `make reset-db` | Empty the database and rebuild the tables (development only) |
| `make demo` | Load the demo wedding (safe to run twice) |
| `make test` | Run the backend tests (about 216) |
| `make lint` | Check the backend code style |
| `make api-types` | Refresh the website's API types (backend must be running) |

When you change a model: `cd backend && .venv/bin/python manage.py makemigrations`, commit the new migration file, and teammates run `make reset-db && make demo` or `manage.py migrate`.

## Payments

The **Payments** page has four numbers (still to collect, collected, still to pay vendors, expected profit) and three sections. Pick one wedding or all of them at the top. The same sections appear in the **Finance** tab of each wedding.

- **From customers:** every invoice (deposit, instalment, extra-guest charge, final payment). Collect it two ways:
  - **Payment link:** creates a private link (valid 1 to 30 days, for the full balance or a part). Copy it, or send it on WhatsApp or email. The customer opens it with no login, sees the couple, the amount and what is already paid, and pays online. The payment is then **recorded automatically**: the invoice, the totals, the dashboard and the planners' screens all update by themselves, and the customer gets a receipt.
  - **Record payment:** for cash, UPI, bank transfer, cheque or card received offline. Choose the date and add a reference. Your name is saved on it.
- **To vendors:** every vendor bill with its advance and final instalments (open the arrow). Vendors are paid offline, so use **Record payment**.
- **History:** every payment in and out, newest first, showing whether it came through a link, online, or was entered by hand and by whom. A payment typed in by mistake can be undone here (the founder is told). Online payments cannot be undone here: refund them in Razorpay.

Extra-guest charges are worked out as (guests above the agreement) x (per-guest rate). Paying more than is left is refused.

Safety rules: a link is a long random token and shows nothing but the amount and who it is for; links expire and can be cancelled; paying twice records once; if the invoice is settled in cash while a customer is paying, the founder gets a "refund needed" alert. Nobody can type in an "online" payment by hand. A vendor bill number can only be entered once per vendor, and a bill with the same vendor and amount due within a week gives a warning. The fake demo checkout works only in development, or when `ALLOW_DEMO_PAYMENTS=true`; with real Razorpay keys and `MOCK_EXTERNALS=false`, customers get the real checkout. For customers to open a link, the website must be reachable from the internet (deploy it, or use a tunnel while testing).

## What is in each folder

```
backend/
  config/           project settings and the main list of web addresses
  accounts/         users and login
  clients/          the couples we work for
  enquiries/        first contact, follow-ups, convert to client
  weddings/         weddings, functions, run sheet, vendor check-in, ratings
  tasks/            the to-do board and the 25+ task template
  vendors/          caterers, decorators, DJs and their details
  quotations/       asking vendors for prices, comparing, picking the winner
  payments/         invoices, payment links, vendor bills, payment history
  portal/           couples' accounts for the customer website (own login, own token)
  ai_tools/         reading quotation PDFs and writing checklists with AI
  notifications/    alerts (bell icon, Telegram)
  incidents/        problems reported during weddings: assign, track, resolve
  dashboard/        the founder's summary page
  live/             instant updates: events go through Redis to every open browser
  common/           shared helpers: who-can-do-what, timed jobs, demo-data command
  demo_data/        the sample wedding used for demos

frontend/src/
  pages/            one folder per screen (dashboard, enquiries, clients, weddings,
                    vendors, quotations, payments, incidents, notifications, login,
                    pay = the customer's payment page, checkin = the vendor's page)
  components/       buttons, tables, forms (common/) and the login guard
  layout/           the sidebar and top bar
  live/             the live connection, pop-ups and the "Live" dot
  login/            who is logged in
  api/              how the website talks to the backend
  helpers/          money (paise to rupees) and date formatting
  types/            API types, made automatically from the backend
```

customer-site/      the couples' website (separate project, port 5174)
  src/pages/        landing (photo slider), sign up / log in, the 4-step profile, home, pay
  public/photos/    put your own photos here: hero-1..4.jpg and gallery-1..5.jpg

Every backend folder follows the same pattern: `models.py` (the data), `serializers.py` (what the API sends and accepts), `views.py` (the logic), `urls.py` (the web addresses), `admin.py` (the admin pages), `tests.py`.

## The customer website

A separate site for the couples, in `customer-site/`. It talks to the same backend under `/api/portal/`.

```bash
cd customer-site && npm install && npm run dev    # http://localhost:5174
```

How it joins the CRM: a couple signs up, which creates an enquiry (source "Website") and alerts the planners. They then fill a 4-step profile (partner, date, city, guests, services, functions, budget, how to contact them). The answers land in the same enquiry and show in a "From the customer website" box in the staff form. When the planner converts the enquiry to a client, the couple's account is linked to it, and the invoices appear on the website with a Pay button. Pay opens the same payment-link page as the WhatsApp link, so there are three ways to pay: a link sent by WhatsApp, a payment typed in by the team, and paying inside the website.

Customer logins are a different kind of token from staff logins, so one can never be used on the other's pages. Set `CUSTOMER_SITE_URL` in `backend/.env` if the site is not on port 5174, and `VITE_WHATSAPP` in `customer-site/.env` for the WhatsApp button.

## Live updates (no refreshing)

When anything changes, the backend publishes a small event to **Redis**, and every logged-in browser receives it over one open connection (**Server-Sent Events**, `GET /api/live/stream/`). The website then refreshes just the screens that event affects, and alerts appear as pop-ups. A green **Live** dot in the top bar shows the connection. If it drops, the website reconnects and catches up on what it missed.

| What happens | Who sees it, instantly |
|---|---|
| A task moves or is assigned | Everyone's task board and the dashboard; the assignee also gets an alert |
| A vendor checks in or is marked late | Event Day screen, wedding page, dashboard; planners get a late alert |
| An incident is reported | All planners get an alert (serious ones also go to Telegram); the incidents list and dashboard update |
| A vendor sends a quotation | Planners get an alert; the comparison table updates |
| A payment is recorded (by link or by hand) | Planners get an alert; the Payments page, the client's balance and the dashboard update |

How it works: `live/signals.py` listens for saves (tasks, arrivals, payments, quotations, incidents, alerts) and publishes events after the database commit, so no other app has to call anything. `live/bus.py` is the Redis connection (publishing takes a millisecond and never fails a save if Redis is down). `live/views.py` is the stream. `frontend/src/live/` reads it. To make something else live, add one handler in `live/signals.py` and list which screens to refresh in `frontend/src/live/LiveProvider.tsx`.

## Background jobs (Celery + Redis)

Timed and slow work runs outside the web request, in a **Celery** worker with Redis as the message queue (`make worker`). The schedule comes from `backend/common/jobs.py`: late-vendor check every minute, vendor payment reminders every morning. Telegram messages are also sent by the worker, so raising an alert never waits on Telegram; if the worker is down, it is sent directly instead. To add a job, write a function in your app and add one line to `common/jobs.py`.

`make worker` uses `--pool=solo` because Celery's default pool does not start on macOS. On a Linux server, drop that flag.

## Optional setups

While `MOCK_EXTERNALS=true` (the default), AI, Razorpay, Telegram and email give fake answers, so demos never break. Alerts then appear only in the bell and the server log.

### Telegram alerts

1. In Telegram, message **@BotFather**, send `/newbot` and follow the steps. Copy the **token** it gives you.
2. Open a chat with your new bot (or add it to a group) and send any message.
3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and copy the number at `"chat":{"id": ...}`.
4. In `.env` set `TELEGRAM_BOT_TOKEN=...`, `TELEGRAM_CHAT_ID=...` and `MOCK_EXTERNALS=false`, then restart the backend and worker.

### Razorpay test payments

1. Create a free account at razorpay.com and switch the dashboard to **Test Mode**.
2. Open Settings -> API Keys -> Generate Test Key. Put the two values in `.env` as `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`, set `MOCK_EXTERNALS=false`, restart.
3. In the test checkout use card `4111 1111 1111 1111` with any future expiry and any CVV, or UPI `success@razorpay`.

### AI

Put `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`, default `gpt-4o-mini`) in `.env` and set `MOCK_EXTERNALS=false`. AI reads quotation PDFs or photos into a draft you can edit, and suggests 25 to 40 tasks for a wedding. Amounts are always converted to paise in our own code, and totals are cross-checked against the line items. If AI is off or fails, a built-in checklist is used.

## Putting it online (not tested yet)

Backend (Render, Railway or similar), with a hosted Postgres and Redis:

```bash
pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput   # build
uvicorn config.asgi:application --host 0.0.0.0 --port $PORT --workers 2                                    # start (not gunicorn's plain workers: they would block live updates)
celery -A config worker --beat -l info                                                                     # second process: background jobs
python manage.py load_demo_data                                                                            # once, for demo data
```

Set these environment variables: `ENVIRONMENT=production`, `SECRET_KEY` (long and random), `DATABASE_URL`, `ALLOWED_HOSTS` (your backend's domain), `FRONTEND_URL` (your website's address), `REDIS_URL` (for example Render Key Value or Upstash), and the settings for the outside services you use. Run exactly **one** Celery process with `--beat`, otherwise every timed job runs twice.

Payment links and the fake checkout: with `MOCK_EXTERNALS=true` the customer's payment page refuses to take payment on a real website (so nobody can "pay" without paying). For a public demo set `ALLOW_DEMO_PAYMENTS=true`; for real payments add the Razorpay keys and set `MOCK_EXTERNALS=false`.

Website (Vercel or Netlify): build command `npm run build`, folder `frontend`, output `dist`, environment variable `VITE_API_URL=https://your-backend-domain/api`.

## Rules we agreed on

- **Money** is always whole **paise** (1 rupee = 100 paise). The website converts for display.
- **Who can do what:** use `allow_roles(Role.PLANNER)` from `common/permissions.py`. The founder passes every check.
- Only Member 1 edits `backend/config/urls.py`, `frontend/src/App.tsx` and the layout. Everyone else works inside their own app folder and page folder.

## Branches and commits

Branches: `feature/member1-core`, `feature/member2-weddings`, `feature/member3-vendors`, `feature/member4-finance-ai`. Merge `main` into your branch first, then open a pull request to `main`; never push to it directly. Keep commits meaningful and fairly large: one commit per finished piece of work, with a clear sentence describing it.
