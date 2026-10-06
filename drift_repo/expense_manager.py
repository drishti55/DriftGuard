import json
import os
from typing import List, Dict, Optional
from config import DEFAULT_DATA_FILE
from utils import get_today_date, parse_date, parse_amount

class ExpenseManager:
    def __init__(self, data_file: str = DEFAULT_DATA_FILE):
        self.data_file = data_file
        self.expenses: List[Dict] = []
        self.load_expenses()

    def load_expenses(self) -> None:
        """Load expenses from JSON storage file."""
        if not os.path.exists(self.data_file):
            self.expenses = []
            return

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                self.expenses = json.load(f)
        except (json.JSONDecodeError, IOError):
            self.expenses = []

    def save_expenses(self) -> None:
        """Save expenses to JSON storage file."""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.expenses, f, indent=2)

    def _generate_id(self) -> int:
        """Generate next sequential integer ID."""
        if not self.expenses:
            return 1
        return max(item["id"] for item in self.expenses) + 1

    def add_expense(
        self,
        amount: float,
        category: str,
        description: str,
        date: Optional[str] = None
    ) -> Dict:
        """Add a new expense item."""
        validated_amount = parse_amount(str(amount))
        validated_date = parse_date(date) if date else get_today_date()

        expense = {
            "id": self._generate_id(),
            "amount": validated_amount,
            "category": category.strip().capitalize(),
            "description": description.strip(),
            "date": validated_date,
        }
        self.expenses.append(expense)
        self.save_expenses()
        return expense

    def list_expenses(self, category: Optional[str] = None) -> List[Dict]:
        """Return all expenses, optionally filtered by category."""
        if not category:
            return list(self.expenses)
        category_lower = category.strip().lower()
        return [
            e for e in self.expenses
            if e["category"].lower() == category_lower
        ]

    def delete_expense(self, expense_id: int) -> bool:
        """Delete an expense by its ID."""
        initial_len = len(self.expenses)
        self.expenses = [e for e in self.expenses if e["id"] != expense_id]
        if len(self.expenses) < initial_len:
            self.save_expenses()
            return True
        return False

    def get_total(self, category: Optional[str] = None) -> float:
        """Calculate total amount of expenses, optionally filtered by category."""
        filtered = self.list_expenses(category=category)
        total = sum(e["amount"] for e in filtered)
        return round(total, 2)
