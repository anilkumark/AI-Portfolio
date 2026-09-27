"""Risk calculation: a real, computable score from portfolio composition."""

from wealth_agent.analysis.stock_position import analyze_portfolio_composition

VOLATILITY_WEIGHTS = {
    "Stock": 8,
    "Commodity": 7,
    "Real Estate": 5,
    "Bond": 3,
    "Cash": 0,
}
CONCENTRATION_THRESHOLD = 40.0  # % in one holding considered concentrated


def calculate_risk(portfolio_id: int) -> dict:
    # Weighted risk score (0-10) from asset-type volatility + concentration flag.
    composition = analyze_portfolio_composition(portfolio_id)
    allocations = composition.get("allocation_by_asset_type", {})

    score = sum(
        pct / 100 * VOLATILITY_WEIGHTS.get(asset_type, 5)
        for asset_type, pct in allocations.items()
    )
    largest = composition.get("largest_holding", {})

    return {
        "portfolio_id": portfolio_id,
        "risk_score": round(score, 2),
        "concentrated": largest.get("allocation", 0) > CONCENTRATION_THRESHOLD,
        "largest_holding": largest,
    }
