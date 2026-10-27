# WishCall — step 1: the website

Manage people, photos and occasions (birthdays, anniversaries, condolences, meetings, achievements, festivals…),
see who is due each day, and import from Excel. Phone calling in your own voice is step 2.

## Run it on your computer

You need **Python 3.10 or newer** (python.org/downloads — on Windows tick "Add Python to PATH" while installing).

**Windows:** double-click `run.bat`
**Mac / Linux:** open a terminal in this folder and run `bash run.sh`

The first start takes a minute (it installs what it needs). Then open **http://localhost:8000**.

On first visit you set your name and a password. Your data is saved in the `data` folder
(`wishcall.db` + `uploads/` for photos) — back up that folder to keep your list safe.

### Open it on your phone (same Wi-Fi)
Find your computer's local IP (Windows: `ipconfig`, Mac: System Settings → Wi-Fi → Details),
then open `http://<that-ip>:8000` on your phone. Windows may ask to allow Python through the firewall — allow it on private networks.

## What works now
- Sign-in with your own password
- **People:** name, photo (camera or upload), mobile, language (English / Hindi / Telugu), group, notes, consent, opt-out
- **Occasions per person:** birthday, wedding anniversary, marriage wishes, death condolence, death anniversary,
  meeting/meetup, achievement, festival, custom — yearly or once, call time, AI replies on/off, custom message,
  and a live preview of what they'll hear in their language
- **Home:** today's wishes, next 4 days, totals
- **Calendar:** wishes per day for any month
- **Excel import:** download the template, upload .xlsx/.csv, see ready / already-there / needs-fixing rows before saving
  (tested with 1,00,000 rows — about 15 seconds)
- **Settings:** your name, calling hours, retries, editable message templates for each language, password change

## Coming in step 2
Your cloned voice (Sarvam), automatic daily calls (Plivo), replies when people talk back, and real call logs.

## Files
```
app/main.py        pages and forms
app/db.py          database (SQLite) and queries
app/logic.py       occasion types, message templates, dates, phone numbers
app/importer.py    Excel / CSV import
app/templates/     page layouts
app/static/        styles and scripts
data/              your database and photos (created on first run)
```
