import argparse
import sys
from expense_manager import ExpenseManager
from utils import format_currency
from tabulate import tabulate

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="A simple command-line expense tracker."
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new expense")
    add_parser.add_argument("--amount", type=float, required=True, help="Expense amount")
    add_parser.add_argument("--cat", type=str, required=True, help="Expense category")
    add_parser.add_argument("--desc", type=str, required=True, help="Expense description")
    add_parser.add_argument("--date", type=str, help="Date (YYYY-MM-DD), defaults to today")

    # List command
    list_parser = subparsers.add_parser("list", help="List recorded expenses")
    list_parser.add_argument("--cat", type=str, help="Filter expenses by category")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete an expense by ID")
    delete_parser.add_argument("--id", type=int, required=True, help="ID of expense to delete")

    # Total command
    total_parser = subparsers.add_parser("total", help="Calculate total expenses")
    total_parser.add_argument("--cat", type=str, help="Filter total by category")

    return parser

def main():
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    manager = ExpenseManager()

    if args.command == "add":
        try:
            expense = manager.add_expense(
                amount=args.amount,
                category=args.cat,
                description=args.desc,
                date=args.date
            )
            print(f"Added expense #{expense['id']}: {expense['description']} ({format_currency(expense['amount'])})")
        except ValueError as err:
            print(f"Error: {err}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "list":
        expenses = manager.list_expenses(category=args.cat)
        if not expenses:
            print("No expenses found.")
            return

        table_data = [
            [e["id"], e["date"], e["category"], format_currency(e["amount"]), e["description"]]
            for e in expenses
        ]
        headers = ["ID", "Date", "Category", "Amount", "Description"]
        print(tabulate(table_data, headers=headers, tablefmt="rounded_grid"))

    elif args.command == "delete":
        success = manager.delete_expense(args.id)
        if success:
            print(f"Expense #{args.id} deleted successfully.")
        else:
            print(f"Expense #{args.id} not found.", file=sys.stderr)
            sys.exit(1)

    elif args.command == "total":
        total = manager.get_total(category=args.cat)
        category_label = f" for '{args.cat}'" if args.cat else ""
        print(f"Total expenses{category_label}: {format_currency(total)}")

if __name__ == "__main__":
    main()
