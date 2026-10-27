"""Occasion types, message templates, dates and phone numbers."""
import calendar
import datetime as dt
import re

LANGS = {"en": "English", "hi": "हिन्दी", "te": "తెలుగు"}
LANG_SHORT = {"en": "EN", "hi": "हि", "te": "తె"}

# key: label, colours, repeats yearly by default, AI replies by default, extra field label + hint
OCCASIONS = {
    "birthday": {"label": "Birthday", "bg": "#FDEBDD", "fg": "#9A3412", "yearly": True, "ai": True, "extra": "", "hint": ""},
    "anniversary": {"label": "Wedding anniversary", "bg": "#FCE7F0", "fg": "#9D174D", "yearly": True, "ai": True, "extra": "", "hint": ""},
    "marriage": {"label": "Marriage wishes", "bg": "#F3E8FF", "fg": "#6B21A8", "yearly": False, "ai": True, "extra": "", "hint": ""},
    "condolence": {"label": "Death condolence", "bg": "#EEF0F3", "fg": "#3F4652", "yearly": False, "ai": False,
                   "extra": "Name of the person who passed", "hint": "e.g. Ramaiah garu"},
    "death_anniversary": {"label": "Death anniversary", "bg": "#EEF0F3", "fg": "#3F4652", "yearly": True, "ai": False,
                          "extra": "Name of the person remembered", "hint": "e.g. Ramaiah garu"},
    "meeting": {"label": "Meeting / meetup", "bg": "#E0F2FE", "fg": "#075985", "yearly": False, "ai": True,
                "extra": "Time and place", "hint": "e.g. 6:00 PM at Banjara Hills"},
    "achievement": {"label": "Achievement", "bg": "#FEF3C7", "fg": "#92400E", "yearly": False, "ai": True,
                    "extra": "What they achieved", "hint": "e.g. your promotion"},
    "festival": {"label": "Festival wishes", "bg": "#ECFCCB", "fg": "#3F6212", "yearly": True, "ai": True,
                 "extra": "Festival name", "hint": "e.g. Diwali"},
    "custom": {"label": "Custom", "bg": "#F1EFE8", "fg": "#444441", "yearly": False, "ai": True,
               "extra": "Occasion name", "hint": "e.g. housewarming"},
}

# Placeholders: {name} {my_name} {detail}
DEFAULT_TEMPLATES = {
    "en": {
        "birthday": "Hello {name}, this is {my_name}. Wishing you a very happy birthday! May this year bring you good health, happiness and success.",
        "anniversary": "Hello {name}, this is {my_name}. Happy wedding anniversary to you both! Wishing you many more years of love and togetherness.",
        "marriage": "Hello {name}, this is {my_name}. Heartiest congratulations on your wedding! Wishing you both a lifetime of happiness.",
        "condolence": "Hello {name}, this is {my_name}. I was deeply saddened to hear about the passing of {detail}. My heartfelt condolences to you and your family.",
        "death_anniversary": "Hello {name}, this is {my_name}. Today I remember {detail} with great respect. My thoughts are with you and your family.",
        "meeting": "Hello {name}, this is {my_name}. Just a reminder about our meeting today, {detail}. Looking forward to seeing you.",
        "achievement": "Hello {name}, this is {my_name}. Congratulations on {detail}! I am truly proud of you.",
        "festival": "Hello {name}, this is {my_name}. Wishing you and your family a very happy {detail}!",
        "custom": "Hello {name}, this is {my_name}. Warm wishes to you on your {detail}!",
    },
    "hi": {
        "birthday": "नमस्ते {name} जी, मैं {my_name} बोल रहा हूँ। आपको जन्मदिन की हार्दिक शुभकामनाएँ! यह साल आपके लिए अच्छी सेहत, खुशियाँ और सफलता लेकर आए।",
        "anniversary": "नमस्ते {name} जी, मैं {my_name} बोल रहा हूँ। आप दोनों को शादी की सालगिरह की हार्दिक बधाई!",
        "marriage": "नमस्ते {name} जी, मैं {my_name} बोल रहा हूँ। विवाह की हार्दिक शुभकामनाएँ! आप दोनों का जीवन खुशियों से भरा रहे।",
        "condolence": "नमस्ते {name} जी, मैं {my_name} बोल रहा हूँ। {detail} के निधन का समाचार सुनकर बहुत दुःख हुआ। आपके और आपके परिवार के प्रति मेरी गहरी संवेदनाएँ।",
        "death_anniversary": "नमस्ते {name} जी, मैं {my_name} बोल रहा हूँ। आज {detail} की पुण्यतिथि पर मैं उन्हें श्रद्धापूर्वक याद करता हूँ।",
        "meeting": "नमस्ते {name} जी, मैं {my_name} बोल रहा हूँ। याद दिला दूँ, आज हमारी मुलाकात है — {detail}।",
        "achievement": "नमस्ते {name} जी, मैं {my_name} बोल रहा हूँ। {detail} के लिए आपको बहुत-बहुत बधाई!",
        "festival": "नमस्ते {name} जी, मैं {my_name} बोल रहा हूँ। आपको और आपके परिवार को {detail} की हार्दिक शुभकामनाएँ!",
        "custom": "नमस्ते {name} जी, मैं {my_name} बोल रहा हूँ। {detail} के अवसर पर आपको हार्दिक शुभकामनाएँ!",
    },
    "te": {
        "birthday": "నమస్కారం {name} గారు, నేను {my_name}. మీకు జన్మదిన శుభాకాంక్షలు! ఈ సంవత్సరం మీకు ఆరోగ్యం, ఆనందం, విజయం కలగాలని కోరుకుంటున్నాను.",
        "anniversary": "నమస్కారం {name} గారు, నేను {my_name}. మీ ఇద్దరికీ పెళ్లి రోజు శుభాకాంక్షలు!",
        "marriage": "నమస్కారం {name} గారు, నేను {my_name}. మీ వివాహ సందర్భంగా హృదయపూర్వక శుభాకాంక్షలు!",
        "condolence": "నమస్కారం {name} గారు, నేను {my_name}. {detail} గారి మరణ వార్త విని చాలా బాధపడ్డాను. మీకు, మీ కుటుంబానికి నా ప్రగాఢ సానుభూతి.",
        "death_anniversary": "నమస్కారం {name} గారు, నేను {my_name}. ఈ రోజు {detail} గారి వర్ధంతి సందర్భంగా వారిని స్మరించుకుంటున్నాను.",
        "meeting": "నమస్కారం {name} గారు, నేను {my_name}. ఈ రోజు మన సమావేశం ఉందని గుర్తు చేస్తున్నాను — {detail}.",
        "achievement": "నమస్కారం {name} గారు, నేను {my_name}. {detail} సందర్భంగా మీకు హృదయపూర్వక అభినందనలు!",
        "festival": "నమస్కారం {name} గారు, నేను {my_name}. మీకు, మీ కుటుంబానికి {detail} శుభాకాంక్షలు!",
        "custom": "నమస్కారం {name} గారు, నేను {my_name}. {detail} సందర్భంగా మీకు శుభాకాంక్షలు!",
    },
}

GROUPS = ["Family", "Friends", "Work", "Community", "Other"]

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def fill(template: str, name: str, my_name: str, detail: str) -> str:
    """Fill placeholders without crashing on stray braces."""
    return (template or "").replace("{name}", name or "").replace("{my_name}", my_name or "") \
        .replace("{detail}", detail or "").strip()


def first_name(full: str) -> str:
    return (full or "").strip().split(" ")[0] if full else ""


# ---------- phone numbers ----------

def normalize_phone(raw) -> str | None:
    """Return +91XXXXXXXXXX for Indian mobiles, +<digits> for other full numbers, else None."""
    if raw is None:
        return None
    s = str(raw).strip()
    if s.endswith(".0"):  # Excel numbers
        s = s[:-2]
    plus = s.startswith("+")
    digits = re.sub(r"\D", "", s)
    if len(digits) == 10 and digits[0] in "6789":
        return "+91" + digits
    if len(digits) == 11 and digits.startswith("0") and digits[1] in "6789":
        return "+91" + digits[1:]
    if len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
        return "+" + digits
    if plus and 8 <= len(digits) <= 15 and not digits.startswith("91"):
        return "+" + digits
    return None


def pretty_phone(p: str) -> str:
    if p and p.startswith("+91") and len(p) == 13:
        return f"+91 {p[3:8]} {p[8:]}"
    return p or ""


# ---------- dates ----------

def valid_day(month: int, day: int, year: int | None) -> bool:
    if not (1 <= month <= 12) or day < 1:
        return False
    if month == 2 and day == 29:
        return year is None or calendar.isleap(year)
    return day <= calendar.monthrange(2001 if year is None else year, month)[1]


def occurs_on(month: int, day: int, year_now: int) -> dt.date:
    """Date of a yearly occasion in a given year (29 Feb falls on 28 Feb in normal years)."""
    if month == 2 and day == 29 and not calendar.isleap(year_now):
        return dt.date(year_now, 2, 28)
    return dt.date(year_now, month, day)


def next_date(occ, today: dt.date) -> dt.date | None:
    m, d, y = occ["month"], occ["day"], occ["year"]
    if occ["recurring"]:
        for yr in (today.year, today.year + 1):
            if y is not None and yr <= y:
                continue
            cand = occurs_on(m, d, yr)
            if cand >= today:
                return cand
        if y is not None and y >= today.year:
            return occurs_on(m, d, y + 1)
        return None
    if y is None:
        return None
    try:
        cand = dt.date(y, m, d)
    except ValueError:
        return None
    return cand if cand >= today else None


def years_since(occ, on: dt.date) -> int | None:
    if occ["recurring"] and occ["year"]:
        n = on.year - occ["year"]
        return n if n > 0 else None
    return None


def short_date(d: dt.date) -> str:
    return f"{d.day} {MONTHS[d.month - 1][:3]}"


def when_label(d: dt.date | None, today: dt.date) -> str:
    if d is None:
        return "Past"
    delta = (d - today).days
    if delta == 0:
        return "today"
    if delta == 1:
        return "tomorrow"
    return short_date(d)


MONTH_WORDS = {m[:3].lower(): i + 1 for i, m in enumerate(MONTHS)}


def parse_date(value) -> tuple[int, int, int | None] | None:
    """Accept Excel dates, dd-mm, dd-mm-yyyy, dd/mm/yyyy, yyyy-mm-dd, '14 Mar', '14 March 1990'."""
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        value = value.date()
    if isinstance(value, dt.date):
        return value.month, value.day, value.year
    s = str(value).strip()
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[ T].*)?", s)
    if m:
        return int(m[2]), int(m[3]), int(m[1])
    m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})(?:[-/.](\d{2,4}))?", s)
    if m:
        y = m[3]
        year = None if y is None else (int(y) + 2000 if len(y) == 2 and int(y) < 50 else
                                       int(y) + 1900 if len(y) == 2 else int(y))
        return int(m[2]), int(m[1]), year
    m = re.fullmatch(r"(\d{1,2})\s*([A-Za-z]{3,})\.?,?\s*(\d{4})?", s)
    if m and m[2][:3].lower() in MONTH_WORDS:
        return MONTH_WORDS[m[2][:3].lower()], int(m[1]), int(m[3]) if m[3] else None
    m = re.fullmatch(r"([A-Za-z]{3,})\.?\s*(\d{1,2}),?\s*(\d{4})?", s)
    if m and m[1][:3].lower() in MONTH_WORDS:
        return MONTH_WORDS[m[1][:3].lower()], int(m[2]), int(m[3]) if m[3] else None
    return None


def parse_time(value) -> str | None:
    """Return HH:MM (24h) or None."""
    if value is None or value == "":
        return None
    if isinstance(value, (dt.time, dt.datetime)):
        return f"{value.hour:02d}:{value.minute:02d}"
    s = str(value).strip().lower().replace(".", ":")
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", s)
    if not m:
        return None
    h, mi, ap = int(m[1]), int(m[2] or 0), m[3]
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if h > 23 or mi > 59:
        return None
    return f"{h:02d}:{mi:02d}"


def time_label(hhmm: str | None) -> str:
    if not hhmm:
        return ""
    h, m = map(int, hhmm.split(":"))
    ap = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {ap}"


# ---------- import aliases ----------

OCCASION_ALIASES = {
    "birthday": "birthday", "bday": "birthday", "birth day": "birthday", "dob": "birthday",
    "anniversary": "anniversary", "wedding anniversary": "anniversary", "marriage anniversary": "anniversary",
    "marriage": "marriage", "wedding": "marriage", "marriage wishes": "marriage",
    "condolence": "condolence", "death": "condolence", "death condolence": "condolence",
    "death anniversary": "death_anniversary", "death_anniversary": "death_anniversary", "punyatithi": "death_anniversary",
    "vardhanti": "death_anniversary",
    "meeting": "meeting", "meetup": "meeting", "meeting / meetup": "meeting",
    "achievement": "achievement", "congrats": "achievement", "congratulations": "achievement",
    "festival": "festival", "festival wishes": "festival",
    "custom": "custom", "other": "custom",
}

LANG_ALIASES = {
    "en": "en", "eng": "en", "english": "en",
    "hi": "hi", "hindi": "hi", "हिन्दी": "hi", "हिंदी": "hi",
    "te": "te", "tel": "te", "telugu": "te", "తెలుగు": "te",
}


def norm_key(s) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s).strip().lower().replace("_", " "))
