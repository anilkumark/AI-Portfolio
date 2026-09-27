from src.analytics.signal_detection import compute_disproportionality


def test_clear_signal_matches_hand_calculated_values():
    # a=10, b=90 (drug X: 100 reports total), c=15, d=1985 (other drugs: 2000 total)
    result = compute_disproportionality("DrugX", "EventY", a=10, b=90, c=15, d=1985)

    assert round(result.prr, 2) == 13.33
    assert round(result.ror, 2) == 14.70
    assert round(result.chi_square, 2) == 69.27
    assert result.is_signal is True


def test_high_prr_but_too_few_cases_is_not_a_signal():
    # a below the minimum case-count floor -- a high ratio on 2 cases is noise
    result = compute_disproportionality("DrugX", "RareEvent", a=2, b=8, c=1, d=1989)
    assert result.a < 3
    assert result.is_signal is False


def test_no_comparator_reports_does_not_divide_by_zero():
    result = compute_disproportionality("DrugX", "EventY", a=5, b=10, c=0, d=0)
    assert result.prr == 0.0
    assert result.is_signal is False


def test_no_reports_for_this_drug_at_all_does_not_divide_by_zero():
    result = compute_disproportionality("DrugX", "EventY", a=0, b=0, c=15, d=1985)
    assert result.prr == 0.0
    assert result.ror == 0.0


def test_zero_comparator_cases_with_real_background_data_is_not_silently_suppressed():
    """Regression test: a=3, b=1, c=0, d=4 -- found by running 8 real
    synthetic case reports through the full local pipeline. Zero OTHER
    drugs have ever reported this event, while real background data
    exists (d=4) -- the strongest possible pattern, not nothing. Before
    the Haldane-Anscombe continuity correction, this returned PRR=0.0 and
    silently failed to signal. Values below independently verified by
    hand: corrected cells (3.5, 1.5, 0.5, 4.5) -> PRR=0.7/0.1=7.0,
    ROR=(3.5*4.5)/(1.5*0.5)=21.0, chi2=10*(15.75-0.75)^2/(5*5*4*6)=3.75."""
    result = compute_disproportionality("DrugX", "EventY", a=3, b=1, c=0, d=4)

    assert round(result.prr, 4) == 7.0
    assert round(result.ror, 4) == 21.0
    assert round(result.chi_square, 4) == 3.75
    # correctly still short of the chi-square threshold at this tiny a
    # real sample -- the fix corrects the math, it doesn't force a signal
    assert result.is_signal is False


def test_proportional_event_rate_is_not_a_signal():
    # drug X's event Y rate matches the background rate exactly -> PRR ~= 1
    result = compute_disproportionality("DrugX", "EventY", a=10, b=90, c=100, d=900)
    assert round(result.prr, 2) == 1.0
    assert result.is_signal is False
