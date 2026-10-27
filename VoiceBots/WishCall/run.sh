#!/usr/bin/env bash
# Start WishCall on Mac / Linux
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv || { echo "Python 3.10+ is needed: https://www.python.org/downloads/"; exit 1; }
fi
. .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo ""
echo "  WishCall is running. Open http://localhost:8000 in your browser."
echo "  Press Ctrl+C here to stop it."
echo ""
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
