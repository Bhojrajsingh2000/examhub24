# ExamHub24

Online competitive exam test series platform built with Django — mock tests, subject-wise
practice questions, current affairs, performance analytics, and premium subscriptions.

## Tech Stack

Python 3.11+, Django 5.x, Bootstrap 5, SQLite (dev) / MySQL or PostgreSQL (production).

## Project Structure

```
ExamHub24/
├── manage.py
├── exam_prep/          # project settings, urls, wsgi/asgi
├── core/                # home page, base template, navbar/footer, context processor
├── accounts/             # custom User model, registration+OTP, login, profile
├── exams/                 # exam categories, exams, subjects
├── questions/             # question bank
├── mock_tests/            # test series, mock tests, the test-attempt UI (timer + navigation)
├── results/                # scoring engine, result pages, leaderboard
├── current_affairs/        # daily current affairs
├── dashboard/               # student & admin dashboards
├── subscriptions/            # plans, user subscriptions
├── payments/                  # Razorpay integration (with a demo/no-keys fallback)
├── study_material/             # notes, PDFs, video lectures
├── notifications/                # in-app notifications
├── analytics/                     # subject/topic-wise performance analytics
├── static/ (css, js, images)
├── templates/ (base.html, navbar, footer)
└── media/ (uploaded questions, study material, profile pictures)
```

## Setup (Local Development)

1. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
   If you don't plan to use MySQL or PostgreSQL locally, you can remove the
   `psycopg2-binary` / `mysqlclient` lines from `requirements.txt` before installing —
   the project runs on SQLite out of the box with no changes.

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Generate a real `SECRET_KEY` (e.g. `python -c "import secrets; print(secrets.token_urlsafe(50))"`)
   and paste it into `.env`. Everything else can be left as-is for local development.

3. **Run migrations and create a superuser**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   ```

3.5. **(Recommended) Seed demo data for testing**
   ```bash
   python manage.py seed_demo_data
   ```
   This creates a demo student login, an exam category/exam/subject, 10 sample questions,
   a free test series with a ready-to-attempt mock test, 3 subscription plans, and a few
   current affairs articles — so you can test the entire platform immediately instead of
   filling the admin panel by hand. See `TESTING_GUIDE.md` for a full test walkthrough.
   Safe to re-run; it won't create duplicates.

4. **Run the development server**
   ```bash
   python manage.py runserver
   ```
   Visit `http://127.0.0.1:8000/` for the site and `http://127.0.0.1:8000/admin/` for
   the admin panel.

5. **Add content via the admin panel** (in this order, since each depends on the last):
   `ExamCategory` → `Exam` → `Subject` → `Question` → `TestSeries` → `MockTest`
   (add questions to it via the inline "Test Questions" section) → `Plan` (for subscriptions).
   Add a `CurrentAffair` or two to see the homepage populated.

## Important Notes

- **You already deployed once — you'll need to migrate again.** This update added new
  model fields (OTP lockout, file-size validators, DB indexes). Run:
  ```bash
  python manage.py makemigrations
  python manage.py migrate
  ```
- **Scheduled tasks (recommended on PythonAnywhere → "Tasks" tab):**
  ```bash
  python manage.py expire_subscriptions          # run daily — downgrades expired premium users
  python manage.py cleanup_abandoned_attempts    # run hourly — auto-submits abandoned tests
  ```
  Without these, expired subscriptions won't lose premium access automatically, and tests
  left open in an abandoned browser tab will stay "in progress" forever.
- **Bulk question upload**: instead of adding questions one at a time in the admin panel,
  generate a template and fill it in:
  ```bash
  python manage.py import_questions_csv --sample sample_questions.csv
  # ...edit the CSV in Excel/Sheets, then:
  python manage.py import_questions_csv sample_questions.csv
  ```
- **Search**: the Test Series page (`/mock-tests/`) and Current Affairs page
  (`/current-affairs/`) now have a search box (title/content, case-insensitive).
- **Coupon codes**: create discount coupons in the admin (Subscriptions → Coupons) —
  percentage or flat discounts, optional per-plan restriction, expiry date, and max-use
  limit. Students enter a code on the plan checkout page. The demo seed data includes a
  `WELCOME20` coupon (20% off) for testing.
- **Health check**: `/health/` returns `{"status": "ok"}` (200) or an error (503) —
  point an uptime monitor (e.g. UptimeRobot, free tier) at this URL.
- **Data safety on delete**: Question/TestQuestion deletion now uses `on_delete=PROTECT`
  instead of `CASCADE` — Django will refuse to delete a question that's already been
  answered by a student (protecting historical results from silently corrupting), and
  will show exactly which records are blocking it. **To retire a question or test, use
  the "Deactivate selected" admin action instead of deleting** — it hides the item from
  new tests while keeping all historical data intact.
- **Admin activity log**: `/dashboard/admin-activity-log/` (linked from the admin
  overview page) shows who added/changed/deleted what, powered by Django's built-in
  audit log — no extra setup needed.
- **Duplicate question finder**: `python manage.py find_duplicate_questions` flags
  likely-duplicate questions (same subject, near-identical text) after bulk imports.
- **Error monitoring (optional)**: set `SENTRY_DSN` in `.env` (free account at
  sentry.io) and `pip install sentry-sdk` to get real-time error alerts with full
  tracebacks instead of only server logs. Leave it blank and nothing changes.
- **Deployment script**: `./deploy.sh` (PythonAnywhere Bash console) pulls latest code,
  installs dependencies, **runs the test suite** (stops the deploy if anything fails),
  applies migrations, and collects static files — then reminds you to click Reload on
  the Web tab (PythonAnywhere doesn't allow that last step to be scripted on the free tier).
- **Caching**: the homepage and per-test leaderboards are now cached (5 min / 60 sec TTL)
  to reduce database load on frequently-hit pages. Cache is invalidated automatically —
  homepage cache clears when an admin adds/edits/deletes an exam category, free test
  series, or current affair; leaderboard cache clears the moment a new attempt is scored.
  Works out of the box with Django's in-memory cache; set `REDIS_URL` in `.env` for a
  real shared cache in a multi-process production deployment (also needed for
  rate-limiting to work correctly with multiple worker processes — see `pip install redis`).
- **Test-attempt double-submit fix**: clicking "Submit Test" used to risk showing the
  browser's native "leave this page?" warning stacked on top of our own confirmation
  dialog (confusing double-prompt), and rapid double-clicking could theoretically submit
  twice. Both are now fixed — the submit button disables itself immediately, and the
  page-leave warning is suppressed once a real submission is underway.
- **Referral program**: every student has a referral code (shown on their Profile page,
  with a one-click copy button). New users can enter a friend's code at signup — once
  they verify their OTP, both accounts get 7 free days of the cheapest active plan
  automatically. Configure the bonus in `subscriptions/services.py` (`REFERRAL_BONUS_DAYS`).
- **Weekly leaderboard**: `/results/weekly-leaderboard/` ranks students by total score
  summed across all tests attempted in the last 7 days — rewards consistent practice,
  not just one strong test. Linked from the dashboard and the per-test leaderboard page.
- **Dark mode**: a moon/sun toggle in the navbar switches the whole site using
  Bootstrap 5.3's built-in dark theme, remembered via `localStorage` (no login needed).
- **Question bookmarking**: bookmark any question from a result's solution page (or
  during Practice Mode) via the star icon — revisit them anytime at `/questions/bookmarks/`.
- **Practice Mode** (`/questions/practice/`): pick a subject, answer one question at a
  time with instant correct/incorrect feedback and explanation — no timer, and it never
  creates a TestAttempt, so it has zero effect on scores/leaderboards/analytics.
- **Video solutions**: add an optional video link per question in the admin
  (Questions → your question → Video Solution URL) — shows as a "Watch video solution"
  link on the result and practice pages when present.
- **PDF result download**: the result page has a "Print / Save as PDF" button that uses
  the browser's native print-to-PDF (no new dependency, works everywhere, print-specific
  CSS hides the navbar/buttons for a clean printout).
- **Sectional/topic-wise practice tests**: on any exam page, click "Build Sectional Test"
  next to a subject to self-generate a short timed test on specific topics (or the whole
  subject) — reuses the full mock-test engine (timer, scoring, results), so no separate
  code path to maintain. Auto-organized into a "Sectional Practice" series per exam.
- **Previous Year Papers category**: `TestSeries` now has a `series_type` field (Mock /
  Previous Year Papers / Sectional) shown as a badge on the test-series listing — set it
  when adding a series in the admin panel.
- **Syllabus checklist tracker**: `/exams/syllabus/<exam-slug>/` (linked from every exam
  page) lets students check off syllabus topics as they study them, with per-subject and
  overall progress bars. Add topics per subject in the admin (Subjects → your subject →
  Syllabus Topics inline).
- **Discussion / doubt section**: every question now has a discussion thread (comments,
  threaded replies, likes, and a "Report" flag for moderation) — linked as "Discuss this
  question" from result pages and Practice Mode. Review flagged comments in the admin
  (Discussion → Discussions, filter by "Flagged").
- **Adaptive recommendations**: the dashboard now shows a "Recommended Practice" widget
  built from each student's weak topics (from `analytics.PerformanceAnalytics`), linking
  straight into a pre-filtered sectional test or practice session for that topic.
- **Multi-language groundwork**: the infrastructure for multiple languages is wired up
  (`LocaleMiddleware`, a language switcher in the navbar, `LANGUAGES = [en, hi]`) but the
  actual Hindi translation strings still need to be written. To translate the site:
  1. Wrap user-facing strings in templates with `{% trans "..." %}` (requires `{% load i18n %}`)
     and in Python code with `from django.utils.translation import gettext as _`.
  2. Run `django-admin makemessages -l hi` to generate `locale/hi/LC_MESSAGES/django.po`.
  3. Fill in the Hindi translations in that `.po` file.
  4. Run `django-admin compilemessages`.
  This wasn't done for the existing English strings in this update (it would touch nearly
  every template) — the switcher itself works today, it just won't change any text yet.
- **Scheduled test window enforcement (bug fix)**: `MockTest.start_date`/`end_date` were
  previously saved by admins but never actually checked — a test scheduled for later, or
  already closed, could be started at any time. Now enforced: students see "opens on..."
  or "this window has closed" messages, and can still resume (but not freshly start) a
  test whose window just closed while they were mid-attempt.
- **Basic PWA support**: the site is now installable (Add to Home Screen) and shows a
  friendly offline page instead of the browser's default error when there's no
  connection — this is app-shell caching only (previously-visited pages/styling work
  offline), not offline test-taking, which still needs a live connection. See
  `static/manifest.json` and `core/templates/core/service_worker.js`.
- **Institutional / bulk licensing**: coaching centers can be added in the admin
  (Institutions → Institutions) with an auto-generated signup code and an optional
  student cap. Students enter that code at registration to link their account; the
  institution's designated admin (or any staff user) gets an aggregate dashboard at
  `/institutions/<id>/dashboard/` (also linked from their own Profile page) showing
  student count, average accuracy, and top performers — without seeing other
  institutions' data.
- **Affiliate / reseller program**: partners get a unique referral link
  (`/payments/go/<code>/`) that stores their code for the visitor's session; if that
  visitor buys a subscription, the partner automatically earns a commission (rate set
  per-partner in the admin, Payments → Affiliate Partners) and can check their own
  earnings at `/payments/affiliate/dashboard/` (linked from Profile once they're set
  up as a partner). This is separate from Coupon codes — an affiliate code tracks
  partner earnings and doesn't need to discount anything for the buyer.
- **Refund handling**: select one or more successful orders in the admin (Payments →
  Orders) and use the "Refund selected orders" action — it revokes the associated
  subscription and downgrades the user from premium (unless they have another still-valid
  subscription). This updates records in our own database only — if you're on a real
  payment gateway, you still need to issue the actual money-back refund in Razorpay's
  own dashboard separately; this action doesn't call any refund API.
- **Free trial**: set `trial_days` on a Plan in the admin to offer a no-payment trial.
  Eligible only for users who've never had any subscription before (paid or trial) —
  shown as a "Start X-Day Free Trial Instead" button on that plan's page.
- **Auto-renewal reminders**: `UserSubscription.auto_renew` (a field that existed before
  but nothing acted on it) is now used — `python manage.py process_auto_renewals` (run
  daily) notifies students 3 days before an auto-renew subscription expires and creates
  a pending order for them to complete. **Note:** this project's payment flow doesn't
  store a reusable card token, so it can't silently auto-charge like a full SaaS
  billing system — the student still completes checkout themselves. Wiring up
  Razorpay's Subscriptions API (which supports real auto-charging via a mandate) would
  be the next step for true silent auto-renewal.
- **Revenue analytics**: the admin overview dashboard now shows revenue this month, MRR
  (monthly-recurring-revenue, normalized across plans of different lengths), active
  subscription count, and this month's churn rate.
- **CI/CD pipeline**: `.github/workflows/ci.yml` runs the full test suite automatically
  on every push/PR if you host this on GitHub — catches a broken change (e.g. a mistake
  in the scoring engine) before it reaches production. No setup needed beyond pushing to
  GitHub; it uses SQLite so there's no database secret to configure.
- **Code coverage**: `.coveragerc` is configured (excludes migrations, management
  commands, tests themselves). Run `coverage run manage.py test && coverage report -m`
  locally, or check the "coverage-report" artifact on any GitHub Actions run.
  `deploy.sh` uses coverage automatically if it's installed.
- **Question preview mode**: in the admin, every question in the list now has a
  "Preview" link showing exactly how it renders to a student (same option layout,
  correct answer highlighted) — catches formatting mistakes (garbled images, near-duplicate
  options) before students see them, without needing a live test to check.
- **Scheduled content publishing**: `CurrentAffair` now has an optional `publish_at`
  datetime — set it to a future time and the article stays hidden from students until
  then, with **no cron job or scheduled task needed** (it's a query-time filter, so
  scheduling is exact to the second rather than depending on a task actually running on
  time). Leave it blank to publish immediately once "Is published" is checked, as before.
- **Log rotation**: application logs now write to `logs/examhub24.log` (auto-created),
  capped at 5 × 5 MB with automatic rotation — prevents unbounded disk usage on a small
  hosting quota. Errors still show in PythonAnywhere's own error log viewer too (console
  handler), this is a secondary on-disk copy for grepping through history.
- **Automated tests**: run `python manage.py test` to check the registration/OTP flow
  and — most importantly — the score-calculation and ranking engine. Run this after any
  future change to `results/models.py` or `accounts/views.py` to catch regressions early.
- **Rate limiting**: login, registration, and OTP endpoints are now throttled (5-10
  attempts per 5-10 minutes per IP) using Django's cache framework. This works out of
  the box locally, but on a real multi-process production server you should point
  `CACHES` in `settings.py` at Redis/Memcached so the counters are shared correctly.
- **Admin URL**: you can move the admin panel off the default `/admin/` path by setting
  `ADMIN_URL=your-custom-path/` in `.env`.
- **Custom User model**: `AUTH_USER_MODEL = 'accounts.User'` is set in `settings.py`.
  This must be in place *before* your first `migrate` — which it already is in this
  project, so just run migrations normally.
- **Payments (demo mode)**: If `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` are left blank
  in `.env`, the payments app automatically simulates an instant successful payment so
  you can test the full subscription flow without a real Razorpay account. Add real
  keys (from https://dashboard.razorpay.com/) to switch to live/test-mode payments.
- **Email/OTP**: With the default console email backend, OTPs and password-reset emails
  are printed to your terminal instead of actually being sent — check the console after
  registering.
- **Media files**: Uploaded question images, study material, and profile pictures are
  served from `/media/` in development. Configure a real storage backend (e.g. AWS S3)
  for production.
- **This code was generated without the ability to run Django in the authoring
  environment (no network access to install packages there).** It has been written
  carefully against Django 5.x conventions, but please run `python manage.py check`
  and `python manage.py makemigrations` right after setup and fix anything your exact
  package versions flag — see the Troubleshooting section below.

## Troubleshooting

- `django.db.utils.OperationalError` on first run → make sure you ran `makemigrations`
  before `migrate`.
- Static files (Bootstrap icons, CSS) missing in production → run
  `python manage.py collectstatic`.
- If `crispy_forms` throws a template-pack error, confirm both `crispy_forms` and
  `crispy_bootstrap5` are in `INSTALLED_APPS` (they already are in this project) and that
  `CRISPY_TEMPLATE_PACK = 'bootstrap5'` is set in `settings.py`.

## Suggested Next Steps

- Add a `discussion` app (question-wise comments) and a DRF-based `api` app for a future
  mobile app — both were suggested as structure additions but not implemented here.
- Add automated tests (`tests.py` in each app) covering registration, test-attempt
  auto-submit, and score calculation.
- Add Celery + Redis for background analytics recalculation instead of doing it
  synchronously on submit (current implementation, fine for small-to-medium scale).
