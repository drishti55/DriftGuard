import pytest
from utils import format_currency, parse_date, parse_amount

def test_format_currency_default():
    assert format_currency(19.99) == "$19.99"
    assert format_currency(5.0) == "$5.00"
    assert format_currency(0) == "$0.00"

def test_format_currency_custom():
    assert format_currency(25.50, currency="€") == "€25.50"

def test_parse_date_valid():
    assert parse_date("2024-03-15") == "2024-03-15"
    assert parse_date("March 15, 2024") == "2024-03-15"

def test_parse_date_invalid():
    with pytest.raises(ValueError):
        parse_date("not-a-date")

def test_parse_amount_valid():
    assert parse_amount("12.34") == 12.34
    assert parse_amount("10") == 10.00
    assert parse_amount(5.5) == 5.50

def test_parse_amount_negative():
    with pytest.raises(ValueError, match="negative"):
        parse_amount("-5.00")

def test_parse_amount_invalid():
    with pytest.raises(ValueError):
        parse_amount("abc")
