"""Hand-verified question/reference pairs, grounded in real policy text
we've read directly from the source documents."""

EVAL_QUESTIONS = [
    {
        "question": "Is water damage from a sewer backup covered by my flood insurance policy?",
        "reference": "Sewer or drain backup damage is excluded from coverage unless a flood in the area was the proximate cause of the backup. If a flood caused the sewer backup, it is covered; otherwise it is excluded.",
    },
    {
        "question": "Does my flood insurance cover damage caused by an earthquake?",
        "reference": "No. The policy excludes loss caused directly by earth movement, including earthquakes, landslides, and land subsidence, even if the earth movement was itself caused by a flood.",
    },
    {
        "question": "What is the maximum amount covered for jewelry damaged in a flood?",
        "reference": "The policy pays no more than $2,500 total for any one loss to jewelry, watches, precious or semi-precious stones, or articles of gold, silver, or platinum.",
    },
]
