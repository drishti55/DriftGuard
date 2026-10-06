import pytest
from expense_manager import ExpenseManager

@pytest.fixture
def manager(tmp_path):
    data_file = tmp_path / "test_expenses.json"
    return ExpenseManager(data_file=str(data_file))

def test_add_expense(manager):
    expense = manager.add_expense(12.50, "Food", "Coffee and pastry")
    assert expense["id"] == 1
    assert expense["amount"] == 12.50
    assert expense["category"] == "Food"
    assert expense["description"] == "Coffee and pastry"
    assert len(manager.expenses) == 1

def test_list_expenses_filtered(manager):
    manager.add_expense(10.00, "Food", "Snack")
    manager.add_expense(25.00, "Transport", "Gas")
    manager.add_expense(15.00, "Food", "Dinner")

    food_items = manager.list_expenses(category="Food")
    assert len(food_items) == 2
    assert all(item["category"] == "Food" for item in food_items)

def test_delete_expense(manager):
    item = manager.add_expense(30.00, "Utilities", "Internet bill")
    assert manager.delete_expense(item["id"]) is True
    assert len(manager.expenses) == 0
    assert manager.delete_expense(999) is False

def test_calculate_total(manager):
    manager.add_expense(10.00, "Food", "Snack")
    manager.add_expense(25.00, "Transport", "Gas")
    total = manager.calculate_total()
    assert total == 35.00
