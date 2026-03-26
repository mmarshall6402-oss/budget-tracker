from flask import Flask, render_template, request, redirect, url_for
import json
import os
from datetime import datetime

app = Flask(__name__)
DATA_FILE = "budget.json"

PRIORITY = {"household": 1, "phone": 2, "debt": 3, "ticket": 4, "other": 5}

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {"cash": 0, "transactions": [], "bills": []}

for key in ["cash", "transactions", "bills"]:
    if key not in data:
        data[key] = [] if key != "cash" else 0

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_balance():
    total_in = sum(t["amount"] for t in data["transactions"] if t["type"] == "in")
    total_out = sum(t["amount"] for t in data["transactions"] if t["type"] == "out")
    return data["cash"] + total_in - total_out

def get_unpaid_bills():
    return [b for b in data["bills"] if b.get("remaining", b["amount"]) > 0]

def get_upcoming_total():
    return sum(b.get("remaining", b["amount"]) for b in data["bills"] if b.get("remaining", b["amount"]) > 0)

def smart_allocate(amount):
    """Given an amount of money, return how to split it across bills smartly."""
    unpaid = sorted(
        [b for b in data["bills"] if b.get("remaining", b["amount"]) > 0],
        key=lambda b: (PRIORITY.get(b.get("category", "other"), 5), b.get("due_days", 999))
    )
    allocations = []
    remaining = amount
    for bill in unpaid:
        if remaining <= 0:
            break
        owed = b_remaining(bill)
        pay = min(owed, remaining)
        if pay > 0:
            allocations.append({"bill_id": bill["id"], "name": bill["name"], "pay": round(pay, 2), "owed": round(owed, 2)})
            remaining -= pay
    return allocations, round(remaining, 2)

def b_remaining(bill):
    return bill.get("remaining", bill["amount"])

@app.route("/")
def index():
    balance = get_balance()
    upcoming_total = get_upcoming_total()
    shortfall = balance - upcoming_total
    bills = sorted(data["bills"],
        key=lambda b: (1 if b_remaining(b) <= 0 else 0,
                       PRIORITY.get(b.get("category","other"),5),
                       b.get("due_days", 999)))
    recent = list(reversed(data["transactions"][-30:]))
    # preview allocation with current balance
    allocations, leftover = smart_allocate(balance) if balance > 0 else ([], 0)
    return render_template("index.html",
        balance=balance,
        cash=data["cash"],
        upcoming_total=upcoming_total,
        shortfall=shortfall,
        bills=bills,
        transactions=recent,
        allocations=allocations,
        leftover=leftover,
        b_remaining=b_remaining)

@app.route("/set_cash", methods=["POST"])
def set_cash():
    data["cash"] = float(request.form.get("cash", 0))
    save_data()
    return redirect(url_for("index"))

@app.route("/add_transaction", methods=["POST"])
def add_transaction():
    t = {
        "id": int(datetime.now().timestamp() * 1000),
        "type": request.form.get("type"),
        "amount": float(request.form.get("amount", 0)),
        "label": request.form.get("label") or ("Income" if request.form.get("type") == "in" else "Expense"),
        "date": datetime.now().strftime("%b %d")
    }
    data["transactions"].append(t)
    save_data()
    return redirect(url_for("index"))

@app.route("/delete_transaction/<int:tid>", methods=["POST"])
def delete_transaction(tid):
    data["transactions"] = [t for t in data["transactions"] if t["id"] != tid]
    save_data()
    return redirect(url_for("index"))

@app.route("/add_bill", methods=["POST"])
def add_bill():
    amount = float(request.form.get("bill_amount", 0))
    bill = {
        "id": int(datetime.now().timestamp() * 1000),
        "name": request.form.get("bill_name"),
        "amount": amount,
        "remaining": amount,
        "due_days": int(request.form.get("due_days") or 999),
        "has_due_date": request.form.get("has_due_date") == "yes",
        "category": request.form.get("category", "other"),
        "paid_toward": 0
    }
    data["bills"].append(bill)
    save_data()
    return redirect(url_for("index"))

@app.route("/pay_toward/<int:bill_id>", methods=["POST"])
def pay_toward(bill_id):
    amount = float(request.form.get("amount", 0))
    for b in data["bills"]:
        if b["id"] == bill_id:
            b["remaining"] = max(0, b.get("remaining", b["amount"]) - amount)
            b["paid_toward"] = b.get("paid_toward", 0) + amount
            # log it as an expense transaction
            data["transactions"].append({
                "id": int(datetime.now().timestamp() * 1000),
                "type": "out",
                "amount": amount,
                "label": f"Payment → {b['name']}",
                "date": datetime.now().strftime("%b %d")
            })
            break
    save_data()
    return redirect(url_for("index"))

@app.route("/apply_allocation", methods=["POST"])
def apply_allocation():
    """Apply the smart allocation — pay toward each bill as suggested."""
    balance = get_balance()
    allocations, _ = smart_allocate(balance)
    for alloc in allocations:
        for b in data["bills"]:
            if b["id"] == alloc["bill_id"]:
                b["remaining"] = max(0, b.get("remaining", b["amount"]) - alloc["pay"])
                b["paid_toward"] = b.get("paid_toward", 0) + alloc["pay"]
                data["transactions"].append({
                    "id": int(datetime.now().timestamp() * 1000),
                    "type": "out",
                    "amount": alloc["pay"],
                    "label": f"Smart pay → {b['name']}",
                    "date": datetime.now().strftime("%b %d")
                })
                break
    save_data()
    return redirect(url_for("index"))

@app.route("/delete_bill/<int:bill_id>", methods=["POST"])
def delete_bill(bill_id):
    data["bills"] = [b for b in data["bills"] if b["id"] != bill_id]
    save_data()
    return redirect(url_for("index"))

@app.route("/clear_transactions", methods=["POST"])
def clear_transactions():
    data["transactions"] = []
    data["cash"] = 0
    save_data()
    return redirect(url_for("index"))

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
