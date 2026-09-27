from wealth_agent.data_query.queries import get_portfolio_holdings


def analyze_portfolio_composition(portfolio_id: int) -> dict:
    # Computes allocation by asset type and identifies the single largest holding.
    holdings = get_portfolio_holdings(portfolio_id)
    if not holdings:
        return {"portfolio_id": portfolio_id, "holdings_count": 0}

    allocation_by_type: dict[str, float] = {}
    for h in holdings:
        allocation_by_type[h["asset_type"]] = allocation_by_type.get(
            h["asset_type"], 0
        ) + float(h["allocation"])

    largest = max(holdings, key=lambda h: float(h["allocation"]))

    return {
        "portfolio_id": portfolio_id,
        "holdings_count": len(holdings),
        "allocation_by_asset_type": allocation_by_type,
        "largest_holding": {
            "name": largest["name"],
            "asset_type": largest["asset_type"],
            "allocation": float(largest["allocation"]),
        },
    }
