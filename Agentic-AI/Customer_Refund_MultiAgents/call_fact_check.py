from fact_check_client import check_groundedness

result = check_groundedness(
    answer="The restocking fee is 20% of $1,500 ($300), reduced by 25% for Gold tier customers ($75 off), giving a final restocking fee of $225.",
    evidence="High-Value Electronics (>$1000): Change of mind: 20% restocking fee. Gold tier: Restocking fees reduced by 25%.",
)
print(result)
