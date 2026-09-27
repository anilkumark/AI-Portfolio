import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.structured_feed import validate_record


def _valid_record(**overrides):
    defaults = {
        "patient_id": "P123", "year_of_birth": "1980", "sex": "F",
        "drug_name": "Drugamab", "event_date": "2026-03-10",
    }
    defaults.update(overrides)
    return defaults


def test_valid_record_passes():
    is_valid, reason = validate_record(_valid_record())
    assert is_valid is True
    assert reason is None


def test_missing_required_field_fails():
    record = _valid_record()
    del record["drug_name"]
    is_valid, reason = validate_record(record)
    assert is_valid is False
    assert "drug_name" in reason


def test_empty_string_field_counts_as_missing():
    is_valid, reason = validate_record(_valid_record(patient_id=""))
    assert is_valid is False
    assert "patient_id" in reason


def test_implausible_birth_year_fails():
    is_valid, reason = validate_record(_valid_record(year_of_birth="1850"))
    assert is_valid is False
    assert "year_of_birth" in reason


def test_future_birth_year_fails():
    is_valid, reason = validate_record(_valid_record(year_of_birth="2099"))
    assert is_valid is False


def test_non_numeric_birth_year_fails():
    is_valid, reason = validate_record(_valid_record(year_of_birth="not-a-year"))
    assert is_valid is False
    assert "not a valid integer" in reason


def test_invalid_sex_value_fails():
    is_valid, reason = validate_record(_valid_record(sex="X"))
    assert is_valid is False
    assert "sex" in reason


def test_malformed_date_fails():
    is_valid, reason = validate_record(_valid_record(event_date="10/03/2026"))
    assert is_valid is False
    assert "event_date" in reason


def test_unknown_sex_code_u_is_accepted():
    is_valid, _ = validate_record(_valid_record(sex="U"))
    assert is_valid is True
