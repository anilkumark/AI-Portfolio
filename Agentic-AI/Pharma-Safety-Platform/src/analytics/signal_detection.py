"""
Disproportionality analysis (PRR / ROR) for one drug-event pair, computed
against a 2x2 contingency table built from the accumulated unified store.
Runs as a scheduled batch job, per the design -- disproportionality is
only meaningful over accumulated data, not per-record, so this has no
real-time variant.

    Event of interest    All other events
Drug of interest    a           b
All other drugs      c           d

PRR = [a/(a+b)] / [c/(c+d)]      -- proportional reporting ratio
ROR = (a*d) / (b*c)               -- reporting odds ratio
chi2 = N*(ad-bc)^2 / [(a+b)(c+d)(a+c)(b+d)]

Signal criteria used here are the standard, widely-cited thresholds
(Evans et al., also the basis for the UK MHRA's routine screening):
a >= 3, PRR >= 2, chi2 >= 4. All three must hold -- a high PRR on 1 or 2
cases is not a signal, it's noise, which is exactly why the case-count
floor exists alongside the ratio.

The math itself is pure and tested without a database. Pulling the (a,b,c,d)
counts for every drug-event pair in the unified store requires Postgres.
"""

from dataclasses import dataclass

MIN_CASE_COUNT = 3
PRR_THRESHOLD = 2.0
CHI_SQUARE_THRESHOLD = 4.0


@dataclass
class DisproportionalityResult:
    drug: str
    event: str
    a: int
    b: int
    c: int
    d: int
    prr: float
    ror: float
    chi_square: float
    is_signal: bool


def compute_disproportionality(drug: str, event: str, a: int, b: int, c: int, d: int) -> DisproportionalityResult:
    """Pure computation over a 2x2 contingency table.

    Two genuinely different zero-cell situations, handled differently:
      - No comparator population exists at all (c+d == 0) or this drug has
        no reports at all (a+b == 0): truly nothing to compute a ratio
        against -- returns 0, not a fabricated number.
      - Real comparator data exists (c+d > 0) but c itself is 0 -- this
        event has literally never been reported for any other drug. That
        is not "no signal," it is potentially the STRONGEST possible
        signal (every observed case involves this one drug), and a naive
        divide-by-zero guard that returns 0.0 here silently suppresses
        exactly the pattern this whole system exists to catch. The
        standard fix for a zero cell with real background data is the
        Haldane-Anscombe continuity correction: add 0.5 to every cell
        before computing the ratio. Applied only to the ratio math --
        the raw a/b/c/d and the MIN_CASE_COUNT check both still use the
        real, uncorrected counts.
    """
    n = a + b + c + d

    if c == 0 and (c + d) > 0:
        ac, bc, cc, dc = a + 0.5, b + 0.5, c + 0.5, d + 0.5
        prr = _safe_ratio(ac, (ac + bc), cc, (cc + dc))
        ror = _safe_odds_ratio(ac, bc, cc, dc)
        chi_square = _safe_chi_square(ac, bc, cc, dc, ac + bc + cc + dc)
    else:
        prr = _safe_ratio(a, (a + b), c, (c + d))
        ror = _safe_odds_ratio(a, b, c, d)
        chi_square = _safe_chi_square(a, b, c, d, n)

    is_signal = (a >= MIN_CASE_COUNT) and (prr >= PRR_THRESHOLD) and (chi_square >= CHI_SQUARE_THRESHOLD)

    return DisproportionalityResult(
        drug=drug, event=event, a=a, b=b, c=c, d=d,
        prr=prr, ror=ror, chi_square=chi_square, is_signal=is_signal,
    )


def _safe_ratio(a: float, a_plus_b: float, c: float, c_plus_d: float) -> float:
    if a_plus_b == 0 or c_plus_d == 0 or c == 0:
        return 0.0
    numerator = a / a_plus_b
    denominator = c / c_plus_d
    return numerator / denominator if denominator != 0 else 0.0


def _safe_odds_ratio(a: float, b: float, c: float, d: float) -> float:
    if b == 0 or c == 0:
        return 0.0
    return (a * d) / (b * c)


def _safe_chi_square(a: float, b: float, c: float, d: float, n: float) -> float:
    row1, row2 = (a + b), (c + d)
    col1, col2 = (a + c), (b + d)
    denominator = row1 * row2 * col1 * col2
    if denominator == 0:
        return 0.0
    return (n * (a * d - b * c) ** 2) / denominator


def run_signal_detection() -> list[DisproportionalityResult]:
    """Builds the (a,b,c,d) contingency table for every drug-event pair
    observed in the unified store, computes disproportionality for each,
    and returns only the pairs that clear the signal threshold.
    REQUIRES a live Postgres instance."""
    from src.common.db import get_connection

    with get_connection() as conn:
        pairs = conn.execute(
            """SELECT DISTINCT de.drug_source_value AS drug, co.condition_source_value AS event
               FROM omop.drug_exposure de
               JOIN omop.condition_occurrence co ON co.person_id = de.person_id
               WHERE de.is_suspect_product = true"""
        ).fetchall()

        results = []
        for pair in pairs:
            drug, event = pair["drug"], pair["event"]

            a = conn.execute(
                """SELECT COUNT(DISTINCT de.person_id) AS n FROM omop.drug_exposure de
                   JOIN omop.condition_occurrence co ON co.person_id = de.person_id
                   WHERE de.drug_source_value = %s AND de.is_suspect_product = true
                     AND co.condition_source_value = %s""",
                (drug, event),
            ).fetchone()["n"]

            b = conn.execute(
                """SELECT COUNT(DISTINCT de.person_id) AS n FROM omop.drug_exposure de
                   JOIN omop.condition_occurrence co ON co.person_id = de.person_id
                   WHERE de.drug_source_value = %s AND de.is_suspect_product = true
                     AND co.condition_source_value != %s""",
                (drug, event),
            ).fetchone()["n"]

            c = conn.execute(
                """SELECT COUNT(DISTINCT de.person_id) AS n FROM omop.drug_exposure de
                   JOIN omop.condition_occurrence co ON co.person_id = de.person_id
                   WHERE de.drug_source_value != %s AND de.is_suspect_product = true
                     AND co.condition_source_value = %s""",
                (drug, event),
            ).fetchone()["n"]

            d = conn.execute(
                """SELECT COUNT(DISTINCT de.person_id) AS n FROM omop.drug_exposure de
                   JOIN omop.condition_occurrence co ON co.person_id = de.person_id
                   WHERE de.drug_source_value != %s AND de.is_suspect_product = true
                     AND co.condition_source_value != %s""",
                (drug, event),
            ).fetchone()["n"]

            results.append(compute_disproportionality(drug, event, a, b, c, d))

    return [r for r in results if r.is_signal]
