# Expense Tracker CLI

A lightweight command-line expense tracker written in Python. Track your daily expenses, filter them by category, view summary totals, and save everything locally in JSON format.

## Features

- Add expenses with amount, category, description, and optional date
- List recorded expenses in a formatted table
- Filter expenses by category
- Calculate total expenses overall or by category
- Delete expenses by ID
- JSON-based persistent storage

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/expense-tracker.git
   cd expense-tracker
   ```

2. Set up a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### 1. Add an Expense
```bash
python main.py add --amount 14.50 --category Food --desc "Lunch burrito"
python main.py add --amount 45.00 --category Transport --desc "Train ticket" --date 2024-03-15
```

### 2. List Expenses
List all recorded expenses:
```bash
python main.py list
```

Filter by category:
```bash
python main.py list --category Food
```

### 3. View Total Expenses
Calculate overall total:
```bash
python main.py total
```

Calculate total for a specific category:
```bash
python main.py total --category Food
```

### 4. Delete an Expense
```bash
python main.py delete --id 1
```

## Running Tests

Run the test suite using pytest:
```bash
pytest
```
