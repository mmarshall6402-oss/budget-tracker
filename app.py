from flask import Flask, render_template, request, redirect, url_for
import json
import os
from datetime import datetime

app = Flask(__name__)
DATA_FILE = "budget.json"

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

def get_upcoming_total():
    return sum(b["amount"] for b in data["bills"] if not b.get("paid", False))

@app.route("/")
def index():
    balance = get_balance()
    upcoming_total = get_upcoming_total()
    shortfall = balance - upcoming_total
    bills = sorted(data["bills"], key=lambda b: b.get("due_days", 999))
    recent = list(reversed(data["transactions"][-30:]))
    return render_template("index.html",
        balance=balance,
        cash=data["cash"],
        upcoming_total=upcoming_total,
        shortfall=shortfall,
        bills=bills,
        transactions=recent)

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
    bill = {
        "id": int(datetime.now().timestamp() * 1000),
        "name": request.form.get("bill_name"),
        "amount": float(request.form.get("bill_amount", 0)),
        "due_days": int(request.form.get("due_days", 30)),
        "paid": False
    }
    data["bills"].append(bill)
    save_data()
    return redirect(url_for("index"))

@app.route("/mark_paid/<int:bill_id>", methods=["POST"])
def mark_paid(bill_id):
    for b in data["bills"]:
        if b["id"] == bill_id:
            b["paid"] = not b.get("paid", False)
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
