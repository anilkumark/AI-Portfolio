"""SQLite storage: schema, settings and the queries the pages need."""
import calendar
import datetime as dt
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from . import logic

BASE = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("WISHCALL_DATA", BASE / "data"))
DB_PATH = DATA / "wishcall.db"
UPLOADS = DATA / "uploads"
IMPORTS = DATA / "imports"

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    grp TEXT NOT NULL DEFAULT 'Friends',
    notes TEXT NOT NULL DEFAULT '',
    photo TEXT,
    consent INTEGER NOT NULL DEFAULT 1,
    opted_out INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS people_phone ON people(phone);
CREATE INDEX IF NOT EXISTS people_name ON people(name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS people_grp ON people(grp);

CREATE TABLE IF NOT EXISTS occasions (
    id INTEGER PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    year INTEGER,
    recurring INTEGER NOT NULL DEFAULT 1,
    call_time TEXT,
    detail TEXT NOT NULL DEFAULT '',
    custom_message TEXT NOT NULL DEFAULT '',
    ai_replies INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS occ_md ON occasions(month, day);
CREATE INDEX IF NOT EXISTS occ_ymd ON occasions(year, month, day);
CREATE INDEX IF NOT EXISTS occ_person ON occasions(person_id);

CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY,
    occasion_id INTEGER REFERENCES occasions(id) ON DELETE SET NULL,
    person_id INTEGER REFERENCES people(id) ON DELETE CASCADE,
    call_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled',
    attempts INTEGER NOT NULL DEFAULT 0,
    duration_s INTEGER NOT NULL DEFAULT 0,
    message TEXT NOT NULL DEFAULT '',
    transcript TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS calls_date ON calls(call_date);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

DEFAULT_SETTINGS = {
    "my_name": "",
    "start_time": "09:30",
    "hours_from": "09:00",
    "hours_to": "20:00",
    "concurrent": "3",
    "retries": "2",
    "retry_gap_min": "60",
    "intro_on": "1",
    "calls_paused": "0",
}


def init():
    for d in (DATA, UPLOADS, IMPORTS):
        d.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    con.commit()
    con.close()


@contextmanager
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


# ---------- settings ----------

def get_settings() -> dict:
    s = dict(DEFAULT_SETTINGS)
    with db() as c:
        for r in c.execute("SELECT key, value FROM settings"):
            s[r["key"]] = r["value"]
    return s


def set_settings(values: dict):
    with db() as c:
        c.executemany("INSERT INTO settings(key, value) VALUES(?, ?) "
                      "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                      [(k, str(v)) for k, v in values.items()])


def template_for(settings: dict, occ_type: str, lang: str) -> str:
    return settings.get(f"tpl:{occ_type}:{lang}") or logic.DEFAULT_TEMPLATES[lang][occ_type]


def all_templates(settings: dict) -> dict:
    return {lang: {t: template_for(settings, t, lang) for t in logic.OCCASIONS} for lang in logic.LANGS}


def message_for(row, settings: dict) -> str:
    """The words this person will hear for this occasion."""
    tpl = row["custom_message"] or template_for(settings, row["type"], row["language"])
    return logic.fill(tpl, logic.first_name(row["name"]), settings.get("my_name") or "[your name]",
                      row["detail"] or logic.OCCASIONS[row["type"]]["label"].lower())


# ---------- occasion queries ----------

OCC_JOIN = """SELECT o.*, p.name, p.phone, p.language, p.photo, p.grp, p.opted_out
              FROM occasions o JOIN people p ON p.id = o.person_id"""


def occasions_on(day: dt.date) -> list:
    """Every occasion that falls on this date (yearly ones match day + month)."""
    params = [day.month, day.day, day.year, day.year, day.month, day.day]
    extra = ""
    if day.month == 2 and day.day == 28 and not calendar.isleap(day.year):
        extra = " OR (o.recurring = 1 AND o.month = 2 AND o.day = 29 AND (o.year IS NULL OR o.year < ?))"
        params.append(day.year)
    sql = (OCC_JOIN + " WHERE (o.recurring = 1 AND o.month = ? AND o.day = ? AND (o.year IS NULL OR o.year < ?))"
           " OR (o.recurring = 0 AND o.year = ? AND o.month = ? AND o.day = ?)" + extra +
           " ORDER BY COALESCE(o.call_time, '99:99'), p.name COLLATE NOCASE")
    with db() as c:
        return c.execute(sql, params).fetchall()


def month_counts(year: int, month: int) -> dict[int, int]:
    counts: dict[int, int] = {}
    with db() as c:
        for r in c.execute("SELECT day, COUNT(*) n FROM occasions WHERE recurring = 1 AND month = ? "
                           "AND (year IS NULL OR year < ?) GROUP BY day", (month, year)):
            d = r["day"]
            if month == 2 and d == 29 and not calendar.isleap(year):
                d = 28
            counts[d] = counts.get(d, 0) + r["n"]
        for r in c.execute("SELECT day, COUNT(*) n FROM occasions WHERE recurring = 0 AND year = ? AND month = ? "
                           "GROUP BY day", (year, month)):
            counts[r["day"]] = counts.get(r["day"], 0) + r["n"]
    return counts


def count_on(day: dt.date) -> int:
    return month_counts(day.year, day.month).get(day.day, 0)


def calls_on(day: dt.date) -> dict[int, sqlite3.Row]:
    with db() as c:
        rows = c.execute("SELECT * FROM calls WHERE call_date = ?", (day.isoformat(),)).fetchall()
    return {r["occasion_id"]: r for r in rows}


# ---------- people ----------

def people_page(q: str, grp: str, page: int, per_page: int = 30):
    where, params = [], []
    if q:
        digits = "".join(ch for ch in q if ch.isdigit())
        if digits and len(digits) >= 3:
            where.append("(p.name LIKE ? OR p.phone LIKE ?)")
            params += [f"%{q}%", f"%{digits}%"]
        else:
            where.append("p.name LIKE ?")
            params.append(f"%{q}%")
    if grp:
        where.append("p.grp = ?")
        params.append(grp)
    w = (" WHERE " + " AND ".join(where)) if where else ""
    with db() as c:
        total = c.execute(f"SELECT COUNT(*) FROM people p{w}", params).fetchone()[0]
        rows = c.execute(f"SELECT p.* FROM people p{w} ORDER BY p.name COLLATE NOCASE, p.id "
                         f"LIMIT ? OFFSET ?", params + [per_page, (page - 1) * per_page]).fetchall()
        ids = [r["id"] for r in rows]
        occs = {}
        if ids:
            marks = ",".join("?" * len(ids))
            for o in c.execute(f"SELECT * FROM occasions WHERE person_id IN ({marks})", ids):
                occs.setdefault(o["person_id"], []).append(o)
    return total, rows, occs


def totals() -> tuple[int, int]:
    with db() as c:
        return (c.execute("SELECT COUNT(*) FROM people").fetchone()[0],
                c.execute("SELECT COUNT(*) FROM occasions").fetchone()[0])


def get_person(pid: int):
    with db() as c:
        p = c.execute("SELECT * FROM people WHERE id = ?", (pid,)).fetchone()
        occ = c.execute("SELECT * FROM occasions WHERE person_id = ? ORDER BY month, day", (pid,)).fetchall()
    return p, occ


def find_person_by_phone(phone: str, exclude_id: int | None = None):
    with db() as c:
        if exclude_id:
            return c.execute("SELECT * FROM people WHERE phone = ? AND id != ?", (phone, exclude_id)).fetchone()
        return c.execute("SELECT * FROM people WHERE phone = ?", (phone,)).fetchone()
