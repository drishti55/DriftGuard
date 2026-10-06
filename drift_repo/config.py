import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_FILE = os.path.join(BASE_DIR, "expenses.json")

DEFAULT_CURRENCY = "$"

VALID_CATEGORIES = [
    "Food",
    "Transport",
    "Housing",
    "Entertainment",
    "Utilities",
    "Health",
    "Other",
]
