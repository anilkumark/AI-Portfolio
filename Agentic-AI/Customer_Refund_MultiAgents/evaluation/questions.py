"""Evaluation questions with known-correct (ground truth) answers, based on the
real content of sop_documents/. Used to measure RAG answer quality with RAGAS.
"""

EVAL_QUESTIONS = [
    {
        "question": (
            "What is the restocking fee for Gold tier electronics on a $1,500 "
            "laptop returned due to change of mind?"
        ),
        "ground_truth": (
            "The restocking fee is 20% of $1,500 ($300), reduced by 25% for "
            "Gold tier customers ($75 off), giving a final restocking fee of "
            "$225 and a refund of $1,275."
        ),
    },
    {
        "question": "What restocking fee applies to clothing returns?",
        "ground_truth": "No restocking fee applies to clothing returns.",
    },
    {
        "question": "What is the minimum refund percentage for electronics returns?",
        "ground_truth": (
            "The minimum refund for electronics is 30% of the original price, "
            "unless denial criteria are met."
        ),
    },
    {
        "question": "What discount do Platinum tier customers get on restocking fees?",
        "ground_truth": "Platinum tier customers get restocking fees reduced by 50%.",
    },
    {
        "question": "What is the maximum restocking fee that can be charged?",
        "ground_truth": (
            "The maximum restocking fee is the lesser of 20% of the price or $500."
        ),
    },
    {
        "question": "What happens to restocking fees during the holiday return period?",
        "ground_truth": (
            "Restocking fees are reduced by 50% for all tiers during the holiday "
            "period (November 1 to January 31), and extended return windows are "
            "automatically applied."
        ),
    },
]
