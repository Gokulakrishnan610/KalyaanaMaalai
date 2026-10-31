# KalyaanaMaalai: Project Guide for the Judges

A walkthrough from "what is Django" to "where exactly is each feature in the code", so every claim can be checked.

> Line numbers are for commit `3975c96` on `main`. If they have moved, search for the class or function name (`Cmd+Shift+F` in VS Code, or `grep -n "name" file`).

## Contents

1. [The project in one page](#1-the-project-in-one-page)
2. [What is Django](#2-what-is-django)
3. [How one request travels: URL, view, serializer, model](#3-how-one-request-travels)
4. [Project structure](#4-project-structure)
5. [My updates, with paths and functions](#5-my-updates-with-paths-and-functions)
6. [Quick navigation table](#6-quick-navigation-table)
7. [Live demo script (8 minutes)](#7-live-demo-script)
8. [Questions the judges may ask](#8-questions-the-judges-may-ask)

---

## 1. The project in one page

**Problem.** Shaandaar Events plans weddings. Enquiries arrive from calls, Instagram and WhatsApp, vendors must be compared and booked, payments are collected from couples and paid to vendors, and on the wedding day things go wrong. All of this lived in chats and notebooks.

**Solution.** One web system that follows a wedding from the first enquiry to the final profit.

```
New enquiry -> consultation and follow-ups -> convert to client -> wedding project
   -> ask 3 vendors for quotes -> compare -> pick the winner (bill + instalments created)
   -> invoices: deposit, instalments, extra guests -> collect by payment link or offline
   -> 25+ task plan, run sheet, vendor check-in on the day, incidents
   -> pay vendors -> profit -> founder dashboard
```

**What makes it more than a form-filling app**

| Feature | One-line explanation |
|---|---|
| Live updates | Screens change by themselves when anyone changes data (no refresh) |
| Payment links | A customer opens a link, pays online, and the payment records itself |
| Incidents | A problem reported on the wedding day alerts planners instantly |
| AI | Reads a vendor's quotation PDF into a draft; suggests a task checklist |
| Background jobs | Late-vendor alerts and payment reminders run on their own |

**Stack:** Django + Django REST Framework (backend API), PostgreSQL (database), Redis (live events and job queue), Celery (background jobs), React + TypeScript + Tailwind (website), Razorpay (online payments, test mode).

---

## 2. What is Django

**Django is a Python web framework.** It gives you the boring, hard parts ready-made, so you only write what is specific to your business:

| Django gives you | What it means for us |
|---|---|
| **ORM** (Object-Relational Mapper) | You describe a table as a Python class; Django creates and queries the table. We never write SQL. |
| **Migrations** | Every change to a model becomes a small file that updates the database safely (`backend/*/migrations/`). |
| **Admin site** | A free screen to view and edit every table at `/admin/`. |
| **URL routing** | A list that says "this web address runs that function". |
| **Authentication and permissions** | Users, passwords (hashed), and rules for who can do what. |
| **Security defaults** | Protection against common attacks (SQL injection, CSRF, clickjacking). |

### Django's pattern: MVT (Model, View, Template)

| Part | Job | In our project |
|---|---|---|
| **Model** | The data (a table) | `models.py` in each app |
| **View** | The logic that handles a request | `views.py` |
| **Template** | The HTML page | **Not used.** Our pages are built by React; Django only sends data. |

### Django REST Framework (DRF): Django as an API

Our website is a separate React app, so Django does not send HTML. It sends **JSON** through an API. DRF adds:

- **Serializers**: convert a model to JSON and back, and **validate** incoming data.
- **ViewSets / APIViews**: ready-made list, create, update, delete handlers.
- **Permissions and throttling**: who may call an endpoint, and how often.
- **Auto-generated API docs**: `/api/docs/` (Swagger), which we also use to generate the website's types.

### Why we chose Django

1. The team knows it, and the code is readable (one pattern in every app).
2. The ORM, migrations and admin saved a lot of time in a 24-hour build.
3. Strong built-in security, important because the system handles money.
4. DRF makes a clean API for the React website, and the same API is documented automatically.

---

## 3. How one request travels

Every feature in the backend follows the same path. A request goes through **five files**, each with one job.

```
Browser (React)
   |  POST /api/enquiries/12/convert/
   v
config/urls.py            1. URL      "which app handles /api/enquiries/...?"
   v
enquiries/urls.py         2. Router   "this address maps to EnquiryViewSet.convert"
   v
enquiries/views.py        3. View     checks permission, reads the request, calls the service
   v
enquiries/serializers.py  4. Serializer  validates the input, shapes the JSON output
   v
enquiries/services.py     5. Service  the business rule (create client, maybe create wedding)
   v
enquiries/models.py       6. Model    the database tables (Enquiry, Client, Wedding)
   v
PostgreSQL                saves the rows; Django returns JSON to the browser
```

### What each file type is for

| File | Use case | Keep out of it | Example in this project |
|---|---|---|---|
| `models.py` | Describe the data and its rules (fields, constraints) | Business flow | `weddings/models.py` `Wedding`: the database itself refuses an end date before the start date and a guest count of 0 |
| `serializers.py` | Validate input and format output (JSON <-> Python) | Business flow | `enquiries/serializers.py` `EnquirySerializer.validate()` makes "Lost needs a reason" |
| `views.py` | Receive the request, check who is asking, call the logic, return a response | Heavy logic | `enquiries/views.py` `EnquiryViewSet.convert()` is 8 lines and calls the service |
| `services.py` | The real business rules (can be reused and tested alone) | HTTP details | `enquiries/services.py` `convert_to_client()` runs in one database transaction |
| `urls.py` | Map web addresses to views | Anything else | `payments/urls.py` lists `pay/<token>/` for the customer page |
| `admin.py` | Configure the free admin screens | | `enquiries/admin.py` |
| `tests.py` | Prove it works (runs against a temporary database) | | `enquiries/tests.py` |

**Why split it like this?** A view stays short and readable, rules live in one place and are easy to test, and the same rule works whether it is called from the website, a background job or a test.

### A worked example: "Convert an enquiry to a client"

| Step | File and function | What happens |
|---|---|---|
| 1 | `backend/config/urls.py` | `path("api/", include("enquiries.urls"))` sends it to the enquiries app |
| 2 | `backend/enquiries/urls.py` | `DefaultRouter` registers `EnquiryViewSet`; `@action convert` becomes `/enquiries/<id>/convert/` |
| 3 | `backend/enquiries/views.py:41` `EnquiryViewSet.convert` | Reads options with `ConvertSerializer`, calls the service |
| 4 | `backend/enquiries/serializers.py:73` `ConvertSerializer` | Validates `create_wedding`, `title`, dates |
| 5 | `backend/enquiries/services.py:10` `convert_to_client` | One transaction: creates the `Client` (or reuses it, so clicking twice never duplicates), sets status Won and win chance 100%, optionally creates the `Wedding` |
| 6 | `backend/enquiries/tests.py` | Test "converting twice makes one client" proves it |

---

## 4. Project structure

```
wedding-management/
  Makefile            shortcuts: make run, make worker, make test, make demo
  docker-compose.yml  PostgreSQL + Redis
  .env.example        every setting (copy to .env)
  README.md           setup and feature guide
  docs/               this guide

  backend/            Django project
    manage.py
    config/           settings.py (all settings), urls.py (main address list), celery.py
    accounts/         users, roles, login (JWT)
    clients/          the couples
    enquiries/        first contact, CRM fields, follow-ups, convert to client
    weddings/         weddings, functions, run sheet, vendor check-in, ratings
    tasks/            the task board and the 25+ task template
    vendors/          vendor directory and categories
    quotations/       quotation requests, comparison, pick the winner
    payments/         invoices, payment links, vendor bills, payment history
    ai_tools/         quotation PDF reading and checklist suggestions
    notifications/    alerts (bell icon, Telegram)
    incidents/        wedding-day problems: report, assign, resolve
    dashboard/        the founder's summary numbers
    live/             live updates: Redis bus, signals, SSE stream
    common/           shared helpers: permissions, pagination, jobs, commands
    demo_data/        the sample "Aarav & Meera" wedding

  frontend/src/       React + TypeScript website
    pages/            one folder per screen
    components/       reusable pieces (buttons, tables, modals, toasts)
    layout/           sidebar and top bar
    live/             live connection, pop-ups, "Live" dot
    login/            who is logged in
    api/              how the website calls the backend
    helpers/          money (paise to rupees) and dates
    types/            API types, generated from the backend
```

**One pattern, every app.** Open any backend folder and you find the same files: `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `tests.py`. Bigger apps add `services.py`.

**Two rules that run through the code**

- **Money is whole paise** (integers). 1 rupee = 100 paise. No decimals, so no rounding errors. The website converts for display (`frontend/src/helpers/money.ts`).
- **Roles:** founder (everything), planner (manages weddings and money), staff (can look, report incidents, work on their tasks). Enforced by `backend/common/permissions.py`.

---

## 5. My updates, with paths and functions

How to read this section: each block says **what** it does, **where** (file and function), and **how to verify** it. Teammates built the Weddings, Vendors/Quotations and the first version of Finance/AI; section 5.10 lists how I joined it all together.

### 5.1 Foundation: project setup, login and shared helpers

| What | Where |
|---|---|
| Project settings (database, JWT login, CORS, Redis, Celery, mock switch) | `backend/config/settings.py`: search `INSTALLED_APPS`, `REST_FRAMEWORK`, `SIMPLE_JWT`, `MOCK_EXTERNALS`, `LIVE_BACKEND`, `ALLOW_DEMO_PAYMENTS` |
| Main address list; mounts every app under `/api/` | `backend/config/urls.py` |
| Custom user (login by email) with role Founder/Planner/Staff | `backend/accounts/models.py:28` `User`, `:6` `Role`, `:12` `UserManager` |
| Login returns a JWT token; throttled to 20 per minute | `backend/accounts/views.py:14` `LoginView.post`; `serializers.py:45` `LoginSerializer.validate` (same error for wrong email or password) |
| "Who am I", and user management (founder only) | `accounts/views.py:31` `MeView`, `:39` `UserViewSet.get_permissions` |
| Role checks used by every app | `backend/common/permissions.py:11` `allow_roles`, `:24` `read_for_all_write_for` |
| Paging (`?page_size=`), phone validation | `common/pagination.py:4` `StandardPagination`; `common/validators.py:4` `check_phone` |
| All data models in one go, with constraints | each `backend/<app>/models.py` (26 models); migrations in `backend/<app>/migrations/` |
| Demo data command (idempotent) | `backend/common/management/commands/load_demo_data.py`, files in `backend/demo_data/` |
| Reset command (dev only) | `backend/common/management/commands/reset_database.py` |
| One-command developer shortcuts | `Makefile`, `docker-compose.yml`, `.env.example` |

**Verify:** `make test` runs 216 tests (login tests in `backend/accounts/tests.py`). Open `http://localhost:8000/api/docs/` to see every endpoint.

### 5.2 CRM: enquiries, follow-ups, clients

| What | Where |
|---|---|
| Enquiry with source (call/Instagram/WhatsApp), stage, budget | `backend/enquiries/models.py:37` `Enquiry` |
| **Odoo-style CRM fields:** expected fee, win chance (auto from stage), priority stars, expected decision date, lost reason | `enquiries/models.py`: `STAGE_WIN_CHANCE`, `LostReason:22`; rules in `enquiries/serializers.py:44` `EnquirySerializer.validate` |
| **Follow-ups** (calls, meetings, messages) with done/overdue | `enquiries/models.py:70` `FollowUp`; `enquiries/views.py:49` `FollowUpViewSet`, `:71` `done` |
| Filters (`?status=`, `?source=`, `?q=`), owner set automatically | `enquiries/views.py:19` `EnquiryViewSet.get_queryset`, `:36` `perform_create` |
| **Convert to client** (safe to click twice; can also start the wedding) | `enquiries/views.py:41` `convert` -> `enquiries/services.py:10` `convert_to_client` |
| Client profile with weddings, history and **what they still owe** | `backend/clients/serializers.py:27` `ClientProfileSerializer`; `clients/views.py:9` `ClientViewSet` |
| Screens | `frontend/src/pages/enquiries/EnquiriesPage.tsx` (table, tabs with counts), `EnquiryBoard.tsx` (drag and drop), `EnquiryForm.tsx`, `FollowUps.tsx`, `StarRating.tsx`; `pages/clients/ClientsPage.tsx`, `ClientPage.tsx` |

**Verify:** tests in `backend/enquiries/tests.py` (`test_convert_makes_one_client_even_when_clicked_twice`, `test_losing_needs_a_reason`, `test_win_chance_follows_the_stage_unless_set_by_hand`). In the app: Enquiries page, drag a card to Lost, and it asks for a reason.

### 5.3 Founder dashboard

| What | Where |
|---|---|
| One endpoint with every number: `GET /api/dashboard/summary/` | `backend/dashboard/views.py:10` `SummaryView`, `dashboard/urls.py` |
| Revenue, expenses, profit per wedding, progress | `backend/dashboard/services.py:27` `wedding_rows`, `:138` `build_summary` |
| Vendor payments due this week (with overdue flag) | `dashboard/services.py:55` `upcoming_vendor_payments` |
| Live activity feed (each alert shown once) | `dashboard/services.py:79` `recent_activity` |
| Follow-ups, incidents, weighted pipeline value | `dashboard/services.py:102` `follow_up_summary`, `:116` `incident_summary`, `:131` `pipeline_value` |
| Screen | `frontend/src/pages/dashboard/DashboardPage.tsx` |

**Verify:** `backend/dashboard/tests.py` (`test_totals_match_the_wedding_rows` proves the dashboard total equals the sum of the rows).

### 5.4 New UI (the design)

| What | Where |
|---|---|
| Colours and fonts (rose accent, dark sidebar, pastel cards) as design tokens | `frontend/src/index.css` (`@theme`) |
| Dark sidebar with icons, top bar with search, bell and the Live dot | `frontend/src/layout/AppLayout.tsx` `AppLayout` |
| Reusable pieces: Button, Card, Input, Modal, Table, Badge, Toasts | `frontend/src/components/common/` |
| Route list; public pages sit outside the login guard | `frontend/src/App.tsx`, guard in `frontend/src/components/RequireLogin.tsx` |
| API client (adds the token, turns errors into messages) | `frontend/src/api/client.ts` |
| Who is logged in; `hasRole()` used to hide buttons | `frontend/src/login/LoginContext.tsx` `LoginProvider`, `useLogin` |

### 5.5 Live updates (no refreshing)

**The idea.** When data changes, the backend publishes a small event to Redis. Every logged-in browser keeps one open connection (Server-Sent Events) and receives it at once. The website then refreshes only the screens that event affects.

```
a Task is saved ---> live/signals.py (post_save) ---> live/bus.py publish()
                                                           |  Redis
browser <--- live/views.py stream (SSE) <------------------+
   |
   +--> frontend/src/live/LiveProvider.tsx: refresh the right screens + show a pop-up
```

| What | Where |
|---|---|
| Redis event bus (fast, never fails a save; in-memory version for tests) | `backend/live/bus.py:109` `publish`, `:52` `RedisBus`, `:29` `MemoryBus`, `:102` `get_bus` |
| **Signals** turn real changes into events (tasks, vendor arrival, quotation, payment, alert, incident, enquiry) | `backend/live/signals.py:62-153` (`task_saved`, `payment_saved`, `quotation_saved`, `incident_changed`, ...) |
| Events sent only after the database commit | `live/signals.py:44` `emit` (uses `transaction.on_commit`) |
| Silence during demo loading | `live/signals.py:36` `silenced` |
| **SSE stream** with login check and role filtering; replays missed events on reconnect | `backend/live/views.py:43` `stream`, `:27` `visible_to`, `:16` `_user_for` |
| Alert to planners and founder (one saved copy each) | `backend/live/alerts.py:6` `notify_roles` |
| Browser side: open stream, reconnect, refresh the right screens, pop-ups | `frontend/src/live/stream.ts` `readStream`, `frontend/src/live/LiveProvider.tsx:18` `REFRESH` map and `:35` `LiveProvider` |
| "Live" dot in the top bar | `frontend/src/live/LiveStatus.tsx` |

**Verify:** `backend/live/tests.py` (11 tests, including that a staff user does **not** receive planner-only events). In the app: open the dashboard in one window, record a payment in another, and watch the numbers change.

### 5.6 Incident management

| What | Where |
|---|---|
| Incident and its history | `backend/incidents/models.py:19` `Incident`, `:45` `IncidentUpdate` |
| Report, assign, change status, add note; each step alerts the right people | `backend/incidents/services.py:21` `report`, `:36` `assign`, `:49` `change_status`, `:65` `add_note` |
| API: anyone reports; planners assign; the assignee or a planner moves it | `backend/incidents/views.py:21` `IncidentViewSet` (`assign:61`, `status:70`, `note:82`, `get_permissions:46`) |
| Screens: list with tabs, report form, detail with history | `frontend/src/pages/incidents/IncidentsList.tsx`, `ReportIncidentForm.tsx`, `IncidentDetail.tsx`; also a tab on the wedding page (`pages/weddings/WeddingDetailPage.tsx`) |

**Verify:** `backend/incidents/tests.py`.

### 5.7 Background jobs with Celery and Redis

| What | Where |
|---|---|
| Celery app and the schedule | `backend/config/celery.py:20` `build_schedule` (reads the list below) |
| **The list of timed jobs**: add one line to add a job | `backend/common/jobs.py` (`JOBS`: late-vendor check every minute, payment reminders at 9 AM) |
| Runs a job by name; runs "run at start" jobs when the worker starts | `backend/common/tasks.py:8` `run_job`, `:15` `run_start_jobs` |
| Telegram sent in the background so alerts never wait | `backend/notifications/tasks.py:7` `send_telegram`; `notifications/services.py:55` `_send_telegram` (falls back to sending directly if the queue is down) |
| The jobs themselves | `backend/weddings/jobs.py` `mark_late_vendors`, `backend/payments/jobs.py` `remind_due_payments` |
| Start it | `make worker` (`Makefile`) |

**Verify:** `backend/common/tests.py`.

### 5.8 Payments rebuild: payment links and offline recording

**What I found first.** I audited every option on the old page with 28 checks; 8 failed (for example, "Pay online" opened the checkout for the planner, anyone could type in a fake online payment, and a mistaken payment could not be undone). Then I rebuilt the page around **two ways to collect**: a **payment link** the customer pays online, and **offline recording**.

**Backend**

| What | Where |
|---|---|
| Payment link data (random token, amount, expiry, status) | `backend/payments/models.py:109` `PaymentLink`; who recorded a payment: `Payment.recorded_by` (`:65`) |
| Create / cancel a link, what the customer sees, start and finish the payment | `backend/payments/links.py`: `create_link:53`, `cancel_link:68`, `public_details:81`, `start_payment:110`, `complete_payment:127` |
| Safety: capped amount, status rules, expiry, "invoice already settled" | `links.py:37` `effective_status`, `:48` `payable_now`, `:76` `online_payments_available` |
| If cash settles an invoice while the customer is paying, tell the founder to refund | `links.py:23` `SettledElsewhere`, handled in `complete_payment` |
| Public endpoints (no login, rate limited, no secrets shown) | `backend/payments/views.py:366` `PublicView`, `:379` `PublicLinkDetails`, `:388` `PublicLinkOrder`, `:394` `PublicLinkVerify` |
| Staff endpoints | `views.py:342` `InvoiceLinks`, `:358` `LinkCancel`, `:285` `AllInvoices`, `:304` `VendorBills`, `:315` `PaymentLedger`, `:332` `PaymentDetail` (undo) |
| Addresses | `backend/payments/urls.py` (`pay/<token>/`, `payment-links/<id>/cancel/`, `payments/`, `finance/vendor-bills/`) |
| Audit fixes | `payments/services.py:22` `MANUAL_METHODS` (no hand-typed "online" payments, cheque added), `:198` `undo_payment`, `:224` `create_invoice` (one deposit per wedding), `:235` `delete_invoice`; future-dated payments rejected in `serializers.py` `PaymentInput.validate_paid_at` |
| Response shapes | `payments/serializers.py:158` `PaymentLinkSerializer`, `:193` `InvoiceRowSerializer`, `:215` `VendorBillSerializer`, `:232` `LedgerSerializer` |
| Razorpay (real in test mode, fake in mock mode) | `backend/payments/razorpay_client.py` (`create_order`, `verify_signature`, `order_details`) |

**Frontend**

| What | Where |
|---|---|
| The Payments page: 4 numbers, 3 tabs | `frontend/src/pages/payments/PaymentsPage.tsx`, `PaymentsWorkspace.tsx`, `StatCards.tsx` |
| From customers: invoices, **Payment link** and **Record payment** buttons | `CustomerPayments.tsx`, `PaymentLinkModal.tsx` (copy / WhatsApp / email), `RecordPaymentModal.tsx`, `NewInvoiceModal.tsx` |
| To vendors: bills with instalments | `VendorPayments.tsx` |
| History with undo | `PaymentHistory.tsx` |
| **The customer's page** (no login): shows the amount, takes payment, shows a receipt | `frontend/src/pages/pay/PublicPayPage.tsx`, `razorpay.ts` |
| Same sections inside each wedding | `FinanceTab.tsx` (loaded by `pages/weddings/Guarded.tsx`) |

**Verify:** `backend/payments/test_links.py` (33 tests, including "a forged confirmation records nothing", "paying twice records once", "an expired link cannot be paid"). I also paid a real Razorpay **test** payment end to end: the receipt showed a genuine Razorpay payment id.

### 5.9 Docs, Git and quality

| What | Where |
|---|---|
| Setup and full feature guide | `README.md` |
| Four-member branch workflow; I merged each member's branch into `main` after checking tests | Git history (`git log --oneline`) |
| History squashed from 53 to a few meaningful commits, then small ones per feature | Git history |
| Tests never touch real services (always the fake Razorpay/AI) | `backend/config/settings.py`: `MOCK_EXTERNALS = "test" in sys.argv or ...` |

### 5.10 Joining the team's parts (integration)

Four people built different modules. These are the problems I found and fixed when merging:

| Problem | Fix | Where |
|---|---|---|
| Late-vendor job closed the test database connection, so 3 tests failed | Skip closing when inside a transaction | `backend/weddings/jobs.py` `_tidy_connections` |
| AI checklist "confirm" passed the wrong arguments to the task template function (which only accepts template tasks) | Save the chosen AI tasks directly, keeping dates and function links | `backend/ai_tools/services.py` `confirm_checklist` |
| Demo data pre-booked a caterer while the three-caterer request was still open, so picking the winner doubled the bill | Removed the pre-booked bill | `backend/demo_data/payments.py` |
| Finance summary figures overlapped | One figure per row | (replaced when the page was rebuilt) |
| "Suggest tasks with AI" button had a placeholder | Plugged in the component | `frontend/src/pages/weddings/TasksTab.tsx` |

**Teammates' modules, for reference**

| Module | Main files |
|---|---|
| Weddings, tasks, event day | `backend/weddings/` (`eventday.py`: `record_arrival`, `mark_late_arrivals`), `backend/tasks/` (`services.py`: `create_tasks_from_template`, `template.py`), `frontend/src/pages/weddings/` |
| Vendors and quotations | `backend/vendors/`, `backend/quotations/` (`services.py`: `select_quotation`), `frontend/src/pages/vendors/`, `quotations/` |
| Base finance, AI, notifications | `backend/payments/services.py`, `backend/ai_tools/services.py` (`extract_quotation`), `backend/notifications/` |

---

## 6. Quick navigation table

| I want to see... | Open |
|---|---|
| How login works | `backend/accounts/views.py` `LoginView`, `backend/accounts/serializers.py` `LoginSerializer` |
| Who can do what | `backend/common/permissions.py` |
| How "convert enquiry to client" works | `backend/enquiries/views.py` `convert` -> `services.py` `convert_to_client` |
| CRM rules (win chance, lost reason) | `backend/enquiries/serializers.py` `EnquirySerializer.validate` |
| Dashboard numbers | `backend/dashboard/services.py` `build_summary` |
| Live updates: publishing | `backend/live/signals.py`, `backend/live/bus.py` |
| Live updates: the stream | `backend/live/views.py` `stream` |
| Live updates: the browser | `frontend/src/live/LiveProvider.tsx` |
| Incidents | `backend/incidents/services.py`, `backend/incidents/views.py` |
| Background jobs | `backend/common/jobs.py`, `backend/config/celery.py` |
| Payment links (logic) | `backend/payments/links.py` |
| Payment links (public endpoints) | `backend/payments/views.py` `PublicLink*` |
| The customer's payment page | `frontend/src/pages/pay/PublicPayPage.tsx` |
| The Payments page | `frontend/src/pages/payments/PaymentsWorkspace.tsx` |
| All routes of the website | `frontend/src/App.tsx` |
| Every API endpoint, interactive | `http://localhost:8000/api/docs/` |
| Every table, editable | `http://localhost:8000/admin/` |
| The database design | `backend/*/models.py` |
| Proof it works | `make test` (216 tests) |

**Commands**

```bash
make run        # backend (uvicorn)
make worker     # background jobs
make demo       # load the demo wedding
make test       # 216 backend tests
cd frontend && npm run dev    # website at http://localhost:5173
```

Demo logins (password `Demo@12345`): `founder@shaandaar.demo`, `planner@shaandaar.demo`, `staff@shaandaar.demo`.

---

## 7. Live demo script

Use two browser windows side by side: window A as the **planner**, window B as the **founder** (or staff).

| Minute | Do this | What the judges see |
|---|---|---|
| 0-1 | Show the dashboard, then `README.md` flow diagram | The whole system and the numbers in one place |
| 1-2 | Enquiries: drag a card on the board; open one and add a follow-up | CRM fields, win chance, overdue follow-up in red |
| 2-3 | Convert an enquiry to a client with "start the wedding project" | One click creates client and wedding; clicking again makes no duplicate |
| 3-4 | Quotations: compare three caterers, pick the winner | Bill and instalments appear under Payments |
| 4-5 | **Incident:** as staff, report "DJ has not arrived" (critical) | In window A a red alert pops up at once and the list updates by itself |
| 5-7 | **Payments:** create a **Payment link**, open it in a private window, press Pay | The customer page, receipt, then window A updates by itself (Collected goes up, link says Paid) |
| 7-7.5 | Record an offline cash payment, then undo it in History | Offline route, audit trail, undo |
| 7.5-8 | Open `http://localhost:8000/api/docs/` and run `make test` | Documented API and 216 passing tests |

**Tip:** in the payment step with `MOCK_EXTERNALS=true` the page shows a "demo mode" button (no real money). With Razorpay test keys it opens the real Razorpay test checkout (domestic test card `4386 2894 0766 0153`, OTP `123456`).

---

## 8. Questions the judges may ask

**Why Django and not Node or Flask?**
It includes the ORM, migrations, admin and security, so we spent the time on the business logic. The code stays consistent (one pattern per app), which matters with four people.

**What are serializers for?**
They validate everything coming in (for example the phone number must be 10 digits, a lost enquiry needs a reason) and shape what goes out. Validation lives in one place instead of being repeated in every view.

**Why a services file?**
So business rules (convert to client, record a payment) are separate from web handling. They are reused by views, background jobs and tests, and are easy to test alone.

**How is money kept accurate?**
All amounts are integers in paise, so there is no rounding. Payments use database transactions and row locks, an `Idempotency-Key` makes a double click record once, and overpaying is refused.

**Is the payment link safe?**
The link is a random token (about 190 bits), expires, can be cancelled, caps the amount to what is owed, and shows only the couple's name, the amount and what for. The server never trusts the browser: it re-checks the payment signature with Razorpay's secret and re-fetches the order amount from Razorpay. A fake confirmation records nothing (tested).

**What if the customer pays online while we record cash?**
The invoice is already settled, so the payment is not double-counted and the founder receives a "REFUND NEEDED" alert.

**How do live updates work without refreshing?**
Django signals publish an event to Redis after each change is saved. A long-lived connection (Server-Sent Events) delivers it to the browser, which refreshes just the affected screens. Events are filtered by role, so a staff member never receives planner-only alerts. If the connection drops, it reconnects and catches up.

**What happens if Redis or the worker is down?**
Saving data still works (a live update that cannot be sent is logged and skipped). Telegram messages fall back to being sent directly.

**Why Celery?**
Timed jobs (late vendors every minute, payment reminders every morning) and slow calls (Telegram) must not block or depend on a web request. Celery runs them in a separate worker.

**How do you know it works?**
216 automated tests (`make test`), including live-update tests, payment-link safety tests and role-permission tests. Tests always use fake outside services, so they never spend real money.

**What is mocked, and what is real?**
With `MOCK_EXTERNALS=true` (default) AI, Razorpay, Telegram and email give fake answers so the demo cannot break. With real keys, Razorpay runs in true test mode: we completed a real test payment through the real checkout.

**What is not finished?**
Deployment to the internet is documented but untested. Customers can only open payment links if the website is reachable from the internet. WhatsApp enquiry capture is manual entry (no automatic import).

**What did you personally build?**
Section 5: the foundation and login, the CRM and dashboard, the new UI, live updates, incident management, Celery background jobs, and the payment-link rebuild, plus joining and fixing the four members' modules.
