"""WishCall web app: people, occasions, calendar, Excel import and settings."""
import calendar as cal
import datetime as dt
import hashlib
import hmac
import json
import secrets
import uuid
from zoneinfo import ZoneInfo

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import db, importer, logic

IST = ZoneInfo("Asia/Kolkata")
APP_DIR = db.BASE / "app"

db.init()
_secret_file = db.DATA / "secret.key"
if not _secret_file.exists():
    _secret_file.write_text(secrets.token_hex(32))

app = FastAPI(title="WishCall", docs_url=None, redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key=_secret_file.read_text().strip(), same_site="lax",
                   max_age=60 * 60 * 24 * 30)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")
templates.env.globals.update(OCCASIONS=logic.OCCASIONS, LANGS=logic.LANGS, LANG_SHORT=logic.LANG_SHORT,
                             GROUPS=logic.GROUPS, MONTHS=logic.MONTHS, time_label=logic.time_label,
                             pretty_phone=logic.pretty_phone)

PHOTO_TYPES = {b"\xff\xd8\xff": ".jpg", b"\x89PNG": ".png", b"RIFF": ".webp"}
MAX_PHOTO = 5 * 1024 * 1024


def today() -> dt.date:
    return dt.datetime.now(IST).date()


# ---------- helpers ----------

def initials(name: str) -> str:
    parts = [p for p in (name or "").split() if p]
    return ((parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")) if parts else "?").upper()


AVATAR_COLOURS = [("#FDEBDD", "#9A3412"), ("#FCE7F0", "#9D174D"), ("#F3E8FF", "#6B21A8"), ("#E0F2FE", "#075985"),
                  ("#FEF3C7", "#92400E"), ("#ECFCCB", "#3F6212"), ("#E6F4F1", "#115E59"), ("#EEF0F3", "#3F4652")]


def avatar(pid: int):
    return AVATAR_COLOURS[(pid or 0) % len(AVATAR_COLOURS)]


templates.env.globals.update(initials=initials, avatar=avatar)


def flash(request: Request, text: str, kind: str = "ok"):
    request.session.setdefault("flash", []).append({"text": text, "kind": kind})


def render(request: Request, name: str, nav: str = "", status_code: int = 200, **ctx):
    msgs = request.session.pop("flash", [])
    return templates.TemplateResponse(request, name, {"nav": nav, "flashes": msgs, **ctx}, status_code=status_code)


def hash_password(pw: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000).hex()
    return f"{salt}${h}"


def check_password(pw: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(pw, salt), stored)


def guard(request: Request):
    """Redirect to setup/login when needed; None means the visitor is signed in."""
    if not db.get_settings().get("password_hash"):
        return RedirectResponse("/setup", 303)
    if not request.session.get("user"):
        return RedirectResponse("/login", 303)
    return None


def go(url: str):
    return RedirectResponse(url, 303)


# ---------- setup & login ----------

@app.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request):
    if db.get_settings().get("password_hash"):
        return go("/login")
    return render(request, "setup.html", error="")


@app.post("/setup")
def setup_save(request: Request, my_name: str = Form(""), password: str = Form(""), password2: str = Form("")):
    if db.get_settings().get("password_hash"):
        return go("/login")
    if len(password) < 8:
        return render(request, "setup.html", error="Use at least 8 characters for the password.", my_name=my_name,
                      status_code=400)
    if password != password2:
        return render(request, "setup.html", error="The two passwords don't match.", my_name=my_name,
                      status_code=400)
    db.set_settings({"password_hash": hash_password(password), "my_name": my_name.strip()})
    request.session["user"] = "admin"
    flash(request, "You're all set. Add your first person to get started.")
    return go("/")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if not db.get_settings().get("password_hash"):
        return go("/setup")
    if request.session.get("user"):
        return go("/")
    return render(request, "login.html", error="")


@app.post("/login")
def login(request: Request, password: str = Form("")):
    stored = db.get_settings().get("password_hash", "")
    if stored and check_password(password, stored):
        request.session["user"] = "admin"
        return go("/")
    return render(request, "login.html", error="That password isn't right.", status_code=401)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return go("/login")


# ---------- home ----------

def build_day_rows(day: dt.date, settings: dict, limit: int | None = None):
    rows = sorted(db.occasions_on(day),
                  key=lambda r: (r["call_time"] or settings["start_time"], r["name"].lower()))
    calls = db.calls_on(day)
    out = []
    for r in rows[:limit] if limit else rows:
        info = logic.OCCASIONS[r["type"]]
        call = calls.get(r["id"])
        n = logic.years_since(r, day)
        bits = []
        if r["type"] == "birthday" and n:
            bits.append(f"Turns {n}")
        elif r["type"] in ("anniversary", "death_anniversary") and n:
            bits.append(f"{n} years")
        if r["detail"]:
            bits.append(r["detail"])
        if not r["ai_replies"]:
            bits.append("Message only")
        when = r["call_time"] or settings["start_time"]
        if r["opted_out"]:
            status, tone = "Opted out", "muted"
        elif call:
            status, tone = {"answered": ("Answered", "ok"), "talked": ("Talked back", "ok"),
                            "retrying": ("Retrying", "warn"), "no_answer": ("No answer", "bad"),
                            "calling": ("Calling…", "warn")}.get(call["status"], ("Scheduled", "muted"))
        else:
            status, tone = logic.time_label(when), "muted"
        out.append({"r": r, "info": info, "detail": " · ".join(bits), "status": status, "tone": tone,
                    "message": db.message_for(r, settings), "when": when})
    return out, len(rows)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    if (r := guard(request)):
        return r
    s = db.get_settings()
    t = today()
    rows, total = build_day_rows(t, s, limit=50)
    done = sum(1 for x in rows if x["status"] in ("Answered", "Talked back"))
    retrying = sum(1 for x in rows if x["tone"] == "warn")
    upcoming = []
    for i in range(1, 5):
        d = t + dt.timedelta(days=i)
        upcoming.append({"dow": d.strftime("%a"), "date": d.day, "count": db.count_on(d),
                         "link": f"/calendar?y={d.year}&m={d.month}&d={d.day}"})
    people_n, occ_n = db.totals()
    now_hm = dt.datetime.now(IST).strftime("%H:%M")
    pending = [x for x in rows if x["tone"] == "muted" and x["status"] != "Opted out"]
    upcoming_rows = [x for x in pending if x["when"] >= now_hm] or pending
    return render(request, "home.html", nav="home", today=t, rows=rows, total=total, done=done,
                  retrying=retrying, scheduled=total - done - retrying, upcoming=upcoming, settings=s,
                  people_n=people_n, occ_n=occ_n, next_row=upcoming_rows[0] if upcoming_rows else None)


@app.post("/pause")
def toggle_pause(request: Request):
    if (r := guard(request)):
        return r
    paused = db.get_settings()["calls_paused"] == "1"
    db.set_settings({"calls_paused": "0" if paused else "1"})
    flash(request, "Calls resumed." if paused else "Calls paused. Nobody will be called until you resume.")
    return go("/")


# ---------- people ----------

@app.get("/people", response_class=HTMLResponse)
def people(request: Request, q: str = "", group: str = "", page: int = 1):
    if (r := guard(request)):
        return r
    page = max(page, 1)
    t = today()
    total, rows, occs = db.people_page(q.strip(), group if group in logic.GROUPS else "", page)
    items = []
    for p in rows:
        upcoming = sorted(((logic.next_date(o, t), o) for o in occs.get(p["id"], [])),
                          key=lambda x: (x[0] is None, x[0] or dt.date.max))
        nxt = upcoming[0] if upcoming and upcoming[0][0] else None
        items.append({"p": p, "next": nxt and {"o": nxt[1], "info": logic.OCCASIONS[nxt[1]["type"]],
                                               "when": logic.when_label(nxt[0], t)},
                      "more": max(len(occs.get(p["id"], [])) - 1, 0)})
    people_n, occ_n = db.totals()
    pages = max((total + 29) // 30, 1)
    return render(request, "people.html", nav="people", items=items, total=total, q=q, group=group, page=page,
                  pages=pages, people_n=people_n, occ_n=occ_n)


def blank_occasion(occ_type: str = "birthday") -> dict:
    info = logic.OCCASIONS[occ_type]
    return {"id": "", "type": occ_type, "day": "", "month": "", "year": "", "recurring": 1 if info["yearly"] else 0,
            "call_time": "", "detail": "", "custom_message": "", "ai_replies": 1 if info["ai"] else 0}


def person_form_ctx(request, person: dict, occasions: list, errors: list, is_new: bool):
    s = db.get_settings()
    return dict(nav="people", person=person, occasions=occasions, errors=errors, is_new=is_new,
                templates_json=json.dumps(db.all_templates(s), ensure_ascii=False).replace("</", "<\\/"),
                occasions_json=json.dumps(logic.OCCASIONS, ensure_ascii=False).replace("</", "<\\/"),
                my_name=s.get("my_name") or "[your name]", blank=blank_occasion())


@app.get("/people/new", response_class=HTMLResponse)
def person_new(request: Request):
    if (r := guard(request)):
        return r
    person = {"id": None, "name": "", "phone": "", "language": "te", "grp": "Friends", "notes": "", "photo": None,
              "consent": 1, "opted_out": 0}
    return render(request, "person_form.html", **person_form_ctx(request, person, [blank_occasion()], [], True))


@app.get("/people/{pid}", response_class=HTMLResponse)
def person_edit(request: Request, pid: int):
    if (r := guard(request)):
        return r
    p, occ = db.get_person(pid)
    if not p:
        flash(request, "That person no longer exists.", "bad")
        return go("/people")
    person = dict(p)
    person["phone"] = p["phone"][3:] if p["phone"].startswith("+91") else p["phone"]
    occasions = [{**dict(o), "year": o["year"] or "", "call_time": o["call_time"] or ""} for o in occ]
    return render(request, "person_form.html", **person_form_ctx(request, person, occasions, [], False))


def _save_photo(upload: UploadFile | None) -> tuple[str | None, str | None]:
    if not upload or not upload.filename:
        return None, None
    data = upload.file.read(MAX_PHOTO + 1)
    if len(data) > MAX_PHOTO:
        return None, "Photo is larger than 5 MB."
    ext = next((e for sig, e in PHOTO_TYPES.items() if data.startswith(sig)), None)
    if ext == ".webp" and data[8:12] != b"WEBP":
        ext = None
    if not ext:
        return None, "Photo must be a JPG, PNG or WebP image."
    name = uuid.uuid4().hex + ext
    (db.UPLOADS / name).write_bytes(data)
    return name, None


async def _save_person(request: Request, pid: int | None):
    form = await request.form()
    errors = []
    name = (form.get("name") or "").strip()
    phone_raw = (form.get("phone") or "").strip()
    phone = logic.normalize_phone(phone_raw)
    language = form.get("language") if form.get("language") in logic.LANGS else "en"
    grp = form.get("grp") if form.get("grp") in logic.GROUPS else "Friends"
    notes = (form.get("notes") or "").strip()
    consent = 1 if form.get("consent") else 0
    opted_out = 1 if form.get("opted_out") else 0
    if not name:
        errors.append("Enter the person's name.")
    if not phone:
        errors.append("Enter a valid 10-digit mobile number.")
    elif (other := db.find_person_by_phone(phone, pid)):
        errors.append(f"This number already belongs to {other['name']}. Add the occasion to their page instead.")

    occasions = []
    cols = ["occ_id", "occ_type", "occ_day", "occ_month", "occ_year", "occ_recurring", "occ_time", "occ_detail",
            "occ_message", "occ_ai"]
    lists = {c: form.getlist(c) for c in cols}
    for i in range(len(lists["occ_type"])):
        g = lambda c: (lists[c][i] if i < len(lists[c]) else "").strip()
        t = g("occ_type")
        if t not in logic.OCCASIONS:
            continue
        o = {"id": g("occ_id"), "type": t, "day": g("occ_day"), "month": g("occ_month"), "year": g("occ_year"),
             "recurring": 1 if g("occ_recurring") == "1" else 0, "call_time": g("occ_time"),
             "detail": g("occ_detail"), "custom_message": g("occ_message"),
             "ai_replies": 1 if g("occ_ai") == "1" else 0}
        label = logic.OCCASIONS[t]["label"]
        if not o["day"] and not o["month"] and not o["year"] and not o["detail"] and not o["custom_message"]:
            if o["id"]:
                errors.append(f"{label}: choose a date, or remove this occasion.")
            occasions.append(o)
            continue
        try:
            d, m = int(o["day"]), int(o["month"])
            y = int(o["year"]) if o["year"] else None
            if y is not None and not (1900 <= y <= 2100):
                raise ValueError
            if not logic.valid_day(m, d, y):
                errors.append(f"{label}: that date doesn't exist.")
            elif not o["recurring"] and y is None:
                errors.append(f"{label}: add the year for a one-time occasion.")
        except ValueError:
            errors.append(f"{label}: choose a day, month and (optional) year.")
        if o["call_time"] and not logic.parse_time(o["call_time"]):
            errors.append(f"{label}: call time isn't valid.")
        occasions.append(o)
    filled = [o for o in occasions if o["day"] or o["month"] or o["id"]]

    photo_name, photo_err = _save_photo(form.get("photo") if hasattr(form.get("photo"), "filename") else None)
    if photo_err:
        errors.append(photo_err)

    person = {"id": pid, "name": name, "phone": phone_raw, "language": language, "grp": grp, "notes": notes,
              "consent": consent, "opted_out": opted_out, "photo": None}
    old = db.get_person(pid)[0] if pid else None
    if old:
        person["photo"] = old["photo"]
    if errors:
        if photo_name:
            (db.UPLOADS / photo_name).unlink(missing_ok=True)
        return render(request, "person_form.html", status_code=400,
                      **person_form_ctx(request, person, occasions or [blank_occasion()], errors, pid is None))

    remove_photo = form.get("remove_photo") == "1"
    new_photo = photo_name or (None if remove_photo else (old["photo"] if old else None))
    with db.db() as c:
        if pid:
            c.execute("UPDATE people SET name=?, phone=?, language=?, grp=?, notes=?, consent=?, opted_out=?, "
                      "photo=?, updated_at=datetime('now') WHERE id=?",
                      (name, phone, language, grp, notes, consent, opted_out, new_photo, pid))
        else:
            pid = c.execute("INSERT INTO people(name, phone, language, grp, notes, consent, opted_out, photo) "
                            "VALUES(?,?,?,?,?,?,?,?)",
                            (name, phone, language, grp, notes, consent, opted_out, new_photo)).lastrowid
        keep = []
        for o in filled:
            vals = (o["type"], int(o["month"]), int(o["day"]), int(o["year"]) if o["year"] else None, o["recurring"],
                    logic.parse_time(o["call_time"]), o["detail"], o["custom_message"], o["ai_replies"])
            if o["id"].isdigit():
                c.execute("UPDATE occasions SET type=?, month=?, day=?, year=?, recurring=?, call_time=?, detail=?, "
                          "custom_message=?, ai_replies=? WHERE id=? AND person_id=?", vals + (int(o["id"]), pid))
                keep.append(int(o["id"]))
            else:
                keep.append(c.execute("INSERT INTO occasions(type, month, day, year, recurring, call_time, detail, "
                                      "custom_message, ai_replies, person_id) VALUES(?,?,?,?,?,?,?,?,?,?)",
                                      vals + (pid,)).lastrowid)
        if keep:
            c.execute(f"DELETE FROM occasions WHERE person_id=? AND id NOT IN ({','.join('?' * len(keep))})",
                      [pid] + keep)
        else:
            c.execute("DELETE FROM occasions WHERE person_id=?", (pid,))
    if old and old["photo"] and old["photo"] != new_photo:
        (db.UPLOADS / old["photo"]).unlink(missing_ok=True)
    flash(request, f"Saved {name}.")
    return go("/people")


@app.post("/people/new")
async def person_create(request: Request):
    if (r := guard(request)):
        return r
    return await _save_person(request, None)


@app.post("/people/{pid}")
async def person_update(request: Request, pid: int):
    if (r := guard(request)):
        return r
    if not db.get_person(pid)[0]:
        return go("/people")
    return await _save_person(request, pid)


@app.post("/people/{pid}/delete")
def person_delete(request: Request, pid: int):
    if (r := guard(request)):
        return r
    p, _ = db.get_person(pid)
    if p:
        with db.db() as c:
            c.execute("DELETE FROM people WHERE id=?", (pid,))
        if p["photo"]:
            (db.UPLOADS / p["photo"]).unlink(missing_ok=True)
        flash(request, f"Deleted {p['name']}.")
    return go("/people")


@app.get("/photo/{name}")
def photo(request: Request, name: str):
    if (r := guard(request)):
        return Response(status_code=404)
    if not all(ch.isalnum() or ch == "." for ch in name):
        return Response(status_code=404)
    f = db.UPLOADS / name
    if not f.exists():
        return Response(status_code=404)
    return FileResponse(f, headers={"Cache-Control": "private, max-age=86400"})


# ---------- calendar ----------

@app.get("/calendar", response_class=HTMLResponse)
def calendar_page(request: Request, y: int | None = None, m: int | None = None, d: int | None = None):
    if (r := guard(request)):
        return r
    t = today()
    y = y if y and 1900 <= y <= 2100 else t.year
    m = m if m and 1 <= m <= 12 else t.month
    last = cal.monthrange(y, m)[1]
    if d is None or not (1 <= d <= last):
        d = t.day if (y, m) == (t.year, t.month) else 1
    sel = dt.date(y, m, d)
    counts = db.month_counts(y, m)
    weeks = cal.Calendar(firstweekday=0).monthdayscalendar(y, m)
    s = db.get_settings()
    rows, total = build_day_rows(sel, s, limit=200)
    prev_m = (y - 1, 12) if m == 1 else (y, m - 1)
    next_m = (y + 1, 1) if m == 12 else (y, m + 1)
    return render(request, "calendar.html", nav="calendar", y=y, m=m, d=d, sel=sel, today=t, counts=counts,
                  weeks=weeks, rows=rows, total=total, prev_m=prev_m, next_m=next_m)


# ---------- calls ----------

@app.get("/calls", response_class=HTMLResponse)
def calls_page(request: Request):
    if (r := guard(request)):
        return r
    with db.db() as c:
        calls = c.execute("SELECT c.*, p.name, p.language, o.type FROM calls c LEFT JOIN people p ON p.id=c.person_id "
                          "LEFT JOIN occasions o ON o.id=c.occasion_id ORDER BY c.updated_at DESC LIMIT 200").fetchall()
    return render(request, "calls.html", nav="calls", calls=calls)


# ---------- settings ----------

@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    if (r := guard(request)):
        return r
    return render(request, "settings.html", nav="settings", s=db.get_settings())


@app.post("/settings")
def settings_save(request: Request, my_name: str = Form(""), start_time: str = Form("09:30"),
                  hours_from: str = Form("09:00"), hours_to: str = Form("20:00"), concurrent: int = Form(3),
                  retries: int = Form(2), retry_gap_min: int = Form(60), intro_on: str = Form("")):
    if (r := guard(request)):
        return r
    times = [logic.parse_time(x) for x in (start_time, hours_from, hours_to)]
    if not all(times):
        flash(request, "Please enter valid times.", "bad")
        return go("/settings")
    if times[1] >= times[2]:
        flash(request, "Calling hours must end after they start.", "bad")
        return go("/settings")
    db.set_settings({"my_name": my_name.strip(), "start_time": times[0], "hours_from": times[1],
                     "hours_to": times[2], "concurrent": max(1, min(concurrent, 20)),
                     "retries": max(0, min(retries, 5)), "retry_gap_min": max(10, min(retry_gap_min, 240)),
                     "intro_on": "1" if intro_on else "0"})
    flash(request, "Settings saved.")
    return go("/settings")


@app.post("/settings/password")
def change_password(request: Request, current: str = Form(""), new: str = Form(""), new2: str = Form("")):
    if (r := guard(request)):
        return r
    if not check_password(current, db.get_settings()["password_hash"]):
        flash(request, "Current password isn't right.", "bad")
    elif len(new) < 8:
        flash(request, "New password needs at least 8 characters.", "bad")
    elif new != new2:
        flash(request, "The new passwords don't match.", "bad")
    else:
        db.set_settings({"password_hash": hash_password(new)})
        flash(request, "Password changed.")
    return go("/settings")


@app.get("/settings/templates", response_class=HTMLResponse)
def templates_page(request: Request, lang: str = "en"):
    if (r := guard(request)):
        return r
    lang = lang if lang in logic.LANGS else "en"
    s = db.get_settings()
    return render(request, "templates.html", nav="settings", lang=lang, tpls=db.all_templates(s)[lang],
                  custom={t: bool(s.get(f"tpl:{t}:{lang}")) for t in logic.OCCASIONS})


@app.post("/settings/templates")
async def templates_save(request: Request):
    if (r := guard(request)):
        return r
    form = await request.form()
    lang = form.get("lang") if form.get("lang") in logic.LANGS else "en"
    vals = {}
    for t in logic.OCCASIONS:
        v = (form.get(f"tpl_{t}") or "").strip()
        vals[f"tpl:{t}:{lang}"] = "" if v == logic.DEFAULT_TEMPLATES[lang][t] else v
    db.set_settings(vals)
    flash(request, f"{logic.LANGS[lang]} templates saved.")
    return go(f"/settings/templates?lang={lang}")


# ---------- import ----------

@app.get("/import", response_class=HTMLResponse)
def import_page(request: Request):
    if (r := guard(request)):
        return r
    return render(request, "import.html", nav="people", result=None, error="")


@app.get("/import/template.xlsx")
def import_template(request: Request):
    if (r := guard(request)):
        return r
    return Response(importer.template_xlsx(),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="wishcall-template.xlsx"'})


@app.post("/import", response_class=HTMLResponse)
async def import_upload(request: Request, file: UploadFile = File(...)):
    if (r := guard(request)):
        return r
    data = await file.read()
    if len(data) > 40 * 1024 * 1024:
        return render(request, "import.html", nav="people", result=None, error="File is larger than 40 MB.",
                      status_code=400)
    try:
        result = importer.check(file.filename or "upload.xlsx", data)
    except ValueError as e:
        return render(request, "import.html", nav="people", result=None, error=str(e), status_code=400)
    except Exception:
        return render(request, "import.html", nav="people", result=None, status_code=400,
                      error="Couldn't read that file. Save it as .xlsx or .csv and try again.")
    return render(request, "import.html", nav="people", result=result, error="")


@app.post("/import/{token}/confirm")
def import_confirm(request: Request, token: str):
    if (r := guard(request)):
        return r
    try:
        people_new, occ_new = importer.commit(token)
    except ValueError as e:
        flash(request, str(e), "bad")
        return go("/import")
    flash(request, f"Imported {occ_new:,} occasions ({people_new:,} new people).")
    return go("/people")


@app.get("/import/{token}/errors.csv")
def import_errors(request: Request, token: str):
    if (r := guard(request)):
        return r
    return Response(importer.errors_csv(token), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="rows-to-fix.csv"'})
