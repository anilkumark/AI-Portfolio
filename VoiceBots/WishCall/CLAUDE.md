# WishCall

A small personal web app for storing people and their occasions (birthday, wedding anniversary, marriage,
condolence, death anniversary, meeting, achievement, festival, custom). On the day, it will call each person and
play a wish in the owner's cloned voice in English, Hindi or Telugu.

- **Step 1 (done):** the website. People, photos, occasions, calendar, Excel import, settings, message templates.
- **Step 2 (next):** cloned voice and speech-to-text (Sarvam), automatic daily calls (Plivo), AI replies when
  people talk back (Gemini), and real call logs. Plivo reaches the app through a cloudflared tunnel
  (`cloudflared tunnel --url http://localhost:8000`), whose URL goes in `PUBLIC_BASE_URL`. The `calls` table and the `/calls` page already exist, but nothing writes to them yet.

Stack: FastAPI + Jinja2 templates + SQLite (Python's built-in `sqlite3`) + plain CSS/JS. No ORM, no JS framework,
no build step.

## Run it

- **Windows:** double-click `run.bat`. **Mac/Linux:** `bash run.sh`.
- Both scripts create `.venv`, install `requirements.txt` and start
  `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- Open http://localhost:8000. The first visit goes to `/setup`, where the owner's name and password are set.
- Manual run on Windows: `.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --reload`.
- Needs Python 3.10+ (the code uses `X | None` types and the `:=` operator).
- `run.bat` tries `py -3` first and falls back to `python`. On machines without the `py` launcher, the
  fallback is what runs.

## Layout

```
app/main.py        FastAPI app: every route, sign-in, forms, photo upload, page context
app/db.py          SQLite schema, connection helper, settings and the queries the pages use
app/logic.py       occasion types, default message templates (en/hi/te), phone and date parsing
app/importer.py    Excel/CSV import: check -> preview -> commit, plus the downloadable template
app/templates/     Jinja pages; base.html is the shell (sidebar + mobile tab bar)
                   _bits.html / _icons.html hold macros, _auth_base.html wraps setup and login
app/static/        style.css and app.js (plain, no bundler)
data/              made at runtime: wishcall.db, uploads/ (photos), imports/ (pending imports), secret.key
```

### Key pieces

- **`db.py`**
  - `db()` is a context manager that opens a connection, commits on exit and turns on foreign keys.
  - `init()` runs the `CREATE TABLE IF NOT EXISTS` schema every time the app starts.
  - Tables: `people`, `occasions` (cascade-deleted with their person), `calls`, and `settings` (key/value).
  - The data folder can be moved with the `WISHCALL_DATA` environment variable.
- **Settings** live in the `settings` table. `DEFAULT_SETTINGS` fills in any key that isn't stored.
  Custom message templates are stored as `tpl:<occasion>:<lang>`. An empty value means "use the default
  from `logic.DEFAULT_TEMPLATES`".
- **Messages:** `db.message_for(row, settings)` returns the exact words a person will hear. It uses the
  occasion's custom message, or the template for that occasion and language, with `{name}`, `{my_name}` and
  `{detail}` filled in. Step 2 should send this text to TTS.
- **Dates:** `db.occasions_on(day)` matches yearly occasions by day and month, and one-time occasions by full
  date. A 29 Feb occasion falls on 28 Feb in non-leap years. `logic.next_date` and `db.month_counts` follow
  the same rule, so any new date code must too.
- **Phones** are stored as `+91XXXXXXXXXX`. `logic.normalize_phone` is the only parser, and a phone number
  identifies a person (no duplicates).
- **Auth:** there is one owner. The password is hashed with PBKDF2. A signed session cookie uses the key in
  `data/secret.key`. Every page route starts with `if (r := guard(request)): return r`.
- **Pages** call `render(request, "x.html", nav=..., **ctx)`. Flash messages go through `flash()`. Forms
  POST, then redirect with `go(url)` (303).

## Rules

1. **Keep it light.** No heavy frameworks: no Django, no SQLAlchemy/ORM, no React/Vue/build tooling, no
   Celery/Redis. Stay on SQLite and raw SQL with `?` parameters. Add a dependency only when the standard
   library can't reasonably do the job, and add it to `requirements.txt` with a `>=` minimum version. Use
   small in-process pieces for background work (for example an asyncio task or thread started on app
   startup), not a separate service.
2. **API keys come only from `.env`.** Never hard-code keys, tokens or account IDs, and never store them in
   SQLite or templates.
   - Read them with `os.environ` after loading `.env` (python-dotenv is fine, or a tiny loader in the code).
   - `.env` is git-ignored. Every new variable must also be added, with an empty value and a comment, to
     `.env.example`.
   - Never log or display key values. The UI may show "connected / not set".
3. **Simulate mode.** Every feature that uses a paid or outside service (Sarvam voice, Plivo calls, any LLM)
   must still work when its keys are missing. The same applies to Gemini replies and to a missing
   `PUBLIC_BASE_URL`.
   - Without keys, the feature runs end to end without network calls. A simulated call still creates `calls`
     rows, moves through statuses (`calling` → `answered` / `no_answer` / `retrying`), stores the message
     text and a fake transcript, and shows up on Home and Call logs.
   - Decide simulate vs live in one place for each service. Show a clear "Simulate mode" badge in the UI.
   - Simulate mode must never spend money or dial a real number.
   - Tests and local checks run in simulate mode by default.
4. **Indian time (Asia/Kolkata) for all scheduling.**
   - Use `main.IST` / `main.today()` (`ZoneInfo("Asia/Kolkata")`). Never use a bare `datetime.now()` or
     `date.today()`, and never rely on the server's own timezone.
   - Call times, calling hours (`hours_from` / `hours_to`), retries and "what's due today" are all IST.
   - SQLite's `datetime('now')` is UTC. That's fine for `created_at` / `updated_at`, but never use it to
     decide when to call.
   - `tzdata` is in `requirements.txt` so `zoneinfo` works on Windows.

## Other things to keep

- Respect `people.opted_out`, `people.consent` and the `calls_paused` setting before any call is placed.
- Language codes are only `en`, `hi`, `te` (`logic.LANGS`). Keep Hindi and Telugu text in UTF-8, and keep
  `ensure_ascii=False` when dumping JSON into pages.
- The importer has been tested with 100,000 rows. Keep it batched and don't add per-row queries.
- `data/` holds personal data (names, phones, photos) and the session key. It must never be committed.
