from datetime import datetime
from dateutil import parser
from config import DEFAULT_CURRENCY

def format_currency(amount: float, currency: str = DEFAULT_CURRENCY) -> str:
    """Format a float amount into a currency string."""
    return f"{currency}{amount:.2f}"

def parse_date(date_str: str) -> str:
    """Parse and normalize date string to YYYY-MM-DD format."""
    try:
        dt = parser.parse(date_str)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        raise ValueError(f"Invalid date format: {date_str}")

def get_today_date() -> str:
    """Return today's date formatted as YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")

def parse_amount(amount_str: str) -> float:
    """Convert amount string to rounded float."""
    try:
        val = float(amount_str)
        if val < 0:
            raise ValueError("Amount cannot be negative")
        return round(val, 2)
    except ValueError as e:
        if "negative" in str(e):
            raise
        raise ValueError(f"Invalid amount: {amount_str}")
