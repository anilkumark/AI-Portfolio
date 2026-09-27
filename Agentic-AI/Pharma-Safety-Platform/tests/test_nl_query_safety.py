import pytest

from src.query.nl_query import UnsafeQueryError, validate_query_is_safe


def test_valid_select_over_omop_passes():
    validate_query_is_safe(
        "SELECT drug_source_value, COUNT(*) FROM omop.drug_exposure GROUP BY drug_source_value"
    )  # should not raise


def test_valid_join_across_omop_tables_passes():
    validate_query_is_safe(
        """SELECT de.drug_source_value, co.condition_source_value
           FROM omop.drug_exposure de
           JOIN omop.condition_occurrence co ON co.person_id = de.person_id"""
    )  # should not raise


def test_delete_statement_rejected():
    # caught by the "must start with SELECT" check before the keyword scan
    # even runs -- still correctly refused either way
    with pytest.raises(UnsafeQueryError, match="SELECT statement"):
        validate_query_is_safe("DELETE FROM omop.person")


def test_drop_table_rejected():
    with pytest.raises(UnsafeQueryError, match="SELECT statement"):
        validate_query_is_safe("DROP TABLE omop.person")


def test_update_statement_rejected():
    with pytest.raises(UnsafeQueryError, match="SELECT statement"):
        validate_query_is_safe("UPDATE omop.person SET sex = 'unknown'")


def test_select_that_smuggles_a_write_keyword_after_a_subquery_is_still_rejected():
    # this one DOES start with SELECT, so it reaches the keyword scan --
    # the actual test of the forbidden-keyword path
    with pytest.raises(UnsafeQueryError, match="forbidden keyword"):
        validate_query_is_safe(
            "SELECT * FROM omop.person WHERE person_id IN (DELETE FROM omop.person RETURNING person_id)"
        )


def test_statement_chaining_rejected():
    with pytest.raises(UnsafeQueryError, match="one statement"):
        validate_query_is_safe("SELECT * FROM omop.person; DROP TABLE omop.person;")


def test_query_reaching_into_operational_schema_rejected():
    with pytest.raises(UnsafeQueryError, match="outside the omop schema"):
        validate_query_is_safe("SELECT * FROM operational.case_records")


def test_query_reaching_into_operational_schema_via_join_rejected():
    with pytest.raises(UnsafeQueryError, match="outside the omop schema"):
        validate_query_is_safe(
            """SELECT * FROM omop.person p
               JOIN operational.case_records c ON c.case_id = p.source_record_id"""
        )


def test_non_select_statement_rejected():
    with pytest.raises(UnsafeQueryError, match="SELECT statement"):
        validate_query_is_safe("EXPLAIN SELECT * FROM omop.person")


def test_empty_query_rejected():
    with pytest.raises(UnsafeQueryError, match="Empty"):
        validate_query_is_safe("   ")


def test_insert_disguised_inside_a_string_literal_is_still_rejected_by_keyword_scan():
    # the naive keyword scan is intentionally conservative -- it would rather
    # over-reject a legitimate query mentioning the word than under-reject
    # an actual write statement
    with pytest.raises(UnsafeQueryError, match="forbidden keyword"):
        validate_query_is_safe(
            "SELECT * FROM omop.observation WHERE value_as_string = 'insert reason here'"
        )
