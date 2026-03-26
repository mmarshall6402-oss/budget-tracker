from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, date
import os
import requests

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://eqfostfkvngrlsrpndhh.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxZm9zdGZrdm5ncmxzcnBuZGhoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ1Mjk5NTUsImV4cCI6MjA5MDEwNTk1NX0.1wKu1OCIhAoAA-OlOqIJ0q9zYcWyoVLlbijh68mwwEU")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

PRIORITY = {"household": 1, "phone": 2, "debt": 3, "ticket": 4, "other": 5}

def db_get(table, order=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}?select=*"
    if order:
        url += f"&order={order}"
    r = requests.get(url, headers=HEADERS)
    return r.json() if r.ok else []

def db_insert(table, row):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    requests.post(url, json=row, headers=HEADERS)

def db_update(table, match_col, match_val, updates):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{match_col}=eq.{match_val}"
    requests.patch(url, json=updates, headers=HEADERS)

def db_delete(table, match_col, match_val):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{match_col}=eq.{match_val}"
    requests.delete(url, headers=HEADERS)

def get_cash():
    rows = db_get("settings")
    for r in rows:
        if r["key"] == "cash":
            return float(r["value"])
    return 0.0

def set_cash_db(amount):
    db_update("settings", "key", "cash", {"value": amount})

def get_balance(transactions, cash):
    total_in = sum(t["amount"] for t in transactions if t["type"] == "in")
    total_out = sum(t["amount"] for t in transactions if t["type"] == "out")
    return cash + total_in - total_out

def b_remaining(bill):
    return bill.get("remaining", bill["amount"])

def calc_due_days(due_date_str):
    try:
        due = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        return max(0, (due - date.today()).days)
    except:
        return 999

def get_upcoming_total(bills):
    return sum(b_remaining(b) for b in bills if b_remaining(b) > 0)

def smart_allocate(bills, amount):
    unpaid = sorted(
        [b for b in bills if b_remaining(b) > 0],
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
            allocations.append({"bill_id": bill["id"], "name": bill["name"], "pay": round(pay, 2)})
            remaining -= pay
    return allocations, round(remaining, 2)

@app.route("/")
def index():
    transactions = db_get("transactions", order="id.desc")
    bills_raw = db_get("bills")
    cash = get_cash()

    # recalc due_days from due_date if present
    bills = []
    for b in bills_raw:
        if b.get("due_date"):
            b["due_days"] = calc_due_days(b["due_date"])
        bills.append(b)

    bills = sorted(bills,
        key=lambda b: (1 if b_remaining(b) <= 0 else 0,
                       PRIORITY.get(b.get("category", "other"), 5),
                       b.get("due_days", 999)))

    balance = get_balance(transactions, cash)
    upcoming_total = get_upcoming_total(bills)
    shortfall = balance - upcoming_total
    allocations, leftover = smart_allocate(bills, balance) if balance > 0 else ([], 0)
    recent = transactions[:30]

    return render_template("index.html",
        balance=balance, cash=cash,
        upcoming_total=upcoming_total,
        shortfall=shortfall, bills=bills,
        transactions=recent,
        allocations=allocations,
        leftover=leftover,
        b_remaining=b_remaining)

@app.route("/set_cash", methods=["POST"])
def set_cash():
    set_cash_db(float(request.form.get("cash", 0)))
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
    db_insert("transactions", t)
    return redirect(url_for("index"))

@app.route("/delete_transaction/<int:tid>", methods=["POST"])
def delete_transaction(tid):
    db_delete("transactions", "id", tid)
    return redirect(url_for("index"))

@app.route("/add_bill", methods=["POST"])
def add_bill():
    amount = float(request.form.get("bill_amount", 0))
    has_due = request.form.get("has_due_date") == "yes"
    due_date = request.form.get("due_date", "") if has_due else ""
    due_days = calc_due_days(due_date) if due_date else 999
    bill = {
        "id": int(datetime.now().timestamp() * 1000),
        "name": request.form.get("bill_name"),
        "amount": amount,
        "remaining": amount,
        "due_days": due_days,
        "due_date": due_date,
        "has_due_date": has_due,
        "category": request.form.get("category", "other"),
        "paid_toward": 0
    }
    db_insert("bills", bill)
    return redirect(url_for("index"))

@app.route("/edit_bill/<int:bill_id>", methods=["POST"])
def edit_bill(bill_id):
    bills = db_get("bills")
    for b in bills:
        if b["id"] == bill_id:
            new_amt = float(request.form.get("amount", b["amount"]))
            diff = new_amt - b["amount"]
            has_due = request.form.get("has_due_date") == "yes"
            due_date = request.form.get("due_date", "") if has_due else ""
            due_days = calc_due_days(due_date) if due_date else 999
            db_update("bills", "id", bill_id, {
                "name": request.form.get("name", b["name"]),
                "amount": new_amt,
                "remaining": max(0, b_remaining(b) + diff),
                "has_due_date": has_due,
                "due_date": due_date,
                "due_days": due_days,
                "category": request.form.get("category", b.get("category", "other"))
            })
            break
    return redirect(url_for("index"))

@app.route("/pay_toward/<int:bill_id>", methods=["POST"])
def pay_toward(bill_id):
    amount = float(request.form.get("amount", 0))
    bills = db_get("bills")
    for b in bills:
        if b["id"] == bill_id:
            actual_pay = min(amount, b_remaining(b))
            db_update("bills", "id", bill_id, {
                "remaining": max(0, b_remaining(b) - actual_pay),
                "paid_toward": b.get("paid_toward", 0) + actual_pay
            })
            db_insert("transactions", {
                "id": int(datetime.now().timestamp() * 1000),
                "type": "out",
                "amount": actual_pay,
                "label": f"Payment → {b['name']}",
                "date": datetime.now().strftime("%b %d")
            })
            break
    return redirect(url_for("index"))

@app.route("/apply_allocation", methods=["POST"])
def apply_allocation():
    transactions = db_get("transactions")
    bills_raw = db_get("bills")
    cash = get_cash()
    bills = []
    for b in bills_raw:
        if b.get("due_date"):
            b["due_days"] = calc_due_days(b["due_date"])
        bills.append(b)
    balance = get_balance(transactions, cash)
    allocations, _ = smart_allocate(bills, balance)
    for alloc in allocations:
        for b in bills:
            if b["id"] == alloc["bill_id"]:
                db_update("bills", "id", b["id"], {
                    "remaining": max(0, b_remaining(b) - alloc["pay"]),
                    "paid_toward": b.get("paid_toward", 0) + alloc["pay"]
                })
                db_insert("transactions", {
                    "id": int(datetime.now().timestamp() * 1000),
                    "type": "out",
                    "amount": alloc["pay"],
                    "label": f"Smart pay → {b['name']}",
                    "date": datetime.now().strftime("%b %d")
                })
                break
    return redirect(url_for("index"))

@app.route("/delete_bill/<int:bill_id>", methods=["POST"])
def delete_bill(bill_id):
    db_delete("bills", "id", bill_id)
    return redirect(url_for("index"))

@app.route("/clear_transactions", methods=["POST"])
def clear_transactions():
    url = f"{SUPABASE_URL}/rest/v1/transactions?id=gte.0"
    requests.delete(url, headers=HEADERS)
    set_cash_db(0)
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
