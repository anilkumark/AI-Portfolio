"""Downloads the real FEMA source documents used throughout this project."""

from pathlib import Path

import requests

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"

SOURCES = {
    "sfip_dwelling_form.pdf": "https://www.fema.gov/sites/default/files/2020-05/F-122_Dwelling_SFIP_102015.pdf",
    "nfip_claims_manual.pdf": "https://www.fema.gov/sites/default/files/documents/fema_nfip-claims-manual_062023.pdf",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (research/learning project)"}


def download_sources() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for filename, url in SOURCES.items():
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        out_path = RAW_DIR / filename
        out_path.write_bytes(response.content)
        print(f"Downloaded {filename} ({len(response.content):,} bytes)")


if __name__ == "__main__":
    download_sources()
