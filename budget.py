import json
import os
from datetime import datetime
import matplotlib.pyplot as plt

DATA_FILE = "budget.json"

# Load or create budget data
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {"income": [], "expenses": []}

# Add income
def add_income(amount, category="Other"):
    data["income"].append({
        "amount": amount,
        "category": category,
        "date": datetime.now().strftime("%Y-%m-%d")
    })

# Add expense
def add_expense(amount, category="Other"):
    data["expenses"].append({
        "amount": amount,
        "category": category,
        "date": datetime.now().strftime("%Y-%m-%d")
    })

# Calculate balance
def get_balance():
    total_income = sum(item["amount"] for item in data["income"])
    total_expense = sum(item["amount"] for item in data["expenses"])
    return total_income - total_expense

# Show report and plot graph
def report():
    print("\n--- Budget Report ---\n")
    
    # Income summary
    income_summary = {}
    for i in data["income"]:
        income_summary[i["category"]] = income_summary.get(i["category"], 0) + i["amount"]
    print("Income:")
    for cat, amt in income_summary.items():
        print(f"  {cat}: ${amt}")
    
    # Expense summary
    expense_summary = {}
    for e in data["expenses"]:
        expense_summary[e["category"]] = expense_summary.get(e["category"], 0) + e["amount"]
    print("\nExpenses:")
    for cat, amt in expense_summary.items():
        print(f"  {cat}: ${amt}")
    
    print(f"\nCurrent Balance: ${get_balance()}\n")
    
    # Plot expenses by category
    if expense_summary:
        plt.bar(expense_summary.keys(), expense_summary.values())
        plt.title("Expenses by Category")
        plt.ylabel("Amount ($)")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

# Save data
def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# CLI menu
def menu():
    while True:
        print("\nSelect an option:")
        print("1. Add Income")
        print("2. Add Expense")
        print("3. Show Report")
        print("4. Exit")
        choice = input("Choice: ")
        
        if choice == "1":
            amt = float(input("Amount: "))
            cat = input("Category (optional): ") or "Other"
            add_income(amt, cat)
            save_data()
            print(f"Added income ${amt} ({cat})")
        elif choice == "2":
            amt = float(input("Amount: "))
            cat = input("Category (optional): ") or "Other"
            add_expense(amt, cat)
            save_data()
            print(f"Added expense ${amt} ({cat})")
        elif choice == "3":
            report()
        elif choice == "4":
            break
        else:
            print("Invalid option")

# Run menu
if __name__ == "__main__":
    menu()
