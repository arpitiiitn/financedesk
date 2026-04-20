"""
FinanceDesk — Flask Backend
Production-ready for Railway / Render / PythonAnywhere deployment.

Data is stored in JSON files in the /data folder.
On Railway, files persist as long as the service is running.
For permanent storage, use the backup endpoint regularly.
"""

from flask import Flask, request, jsonify, render_template, send_file
import json, os, uuid, math, io, zipfile
from datetime import datetime

app = Flask(__name__)

# ── Secret key (set SECRET_KEY env variable on Railway) ──────────────────────
app.secret_key = os.environ.get("SECRET_KEY", "financedesk-local-key-change-me")

# ── Allow large uploads (base64 images can be several MB each) ───────────────
# 50MB limit — enough for many high-res photos
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

# ── CORS — allow browser to call API from any origin ──────────────────────────
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    return response

@app.route("/api/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    return "", 204

# ── Data directory ─────────────────────────────────────────────────────────────
# On Railway the working directory is /app, so data goes to /app/data
DATA_DIR       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CLIENTS_FILE   = os.path.join(DATA_DIR, "clients.json")
LOANS_FILE     = os.path.join(DATA_DIR, "loans.json")
PAYMENTS_FILE  = os.path.join(DATA_DIR, "payments.json")
PURCHASES_FILE = os.path.join(DATA_DIR, "purchases.json")

# ── Make data dir on startup ───────────────────────────────────────────────────
os.makedirs(DATA_DIR, exist_ok=True)

# ── JSON helpers ───────────────────────────────────────────────────────────────
def read_json(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def write_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

def now_str():
    return datetime.now().strftime("%Y-%m-%d")

# ── Interest Calculations ──────────────────────────────────────────────────────
def calculate_interest(principal, rate, start_date, interest_type):
    """
    Simple Interest  : SI = P × R × T / 100
      where R = monthly rate %, T = months elapsed

    Compound Interest: A = P × (1 + R/100)^(T/12)
      where R = annual rate %, annual compounding
    """
    try:
        start      = datetime.strptime(start_date, "%Y-%m-%d")
        delta_days = (datetime.now() - start).days
        t          = max(0, delta_days / 30.0)   # months elapsed
        p          = float(principal)
        r          = float(rate)

        if interest_type == "compound":
            # Annual compounding
            a        = p * math.pow(1 + r / 100, t / 12)
            interest = a - p
        else:
            # Monthly simple interest
            interest = (p * r * t) / 100
            a        = p + interest

        return round(interest, 2), round(a, 2)
    except Exception:
        return 0.0, float(principal)

# ── Serve frontend ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

# ── Health check (Railway uses this) ──────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "FinanceDesk"})

# ══════════════════════════════════════════════════════════════════════════════
#  CLIENTS
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/clients", methods=["GET"])
def get_clients():
    clients = read_json(CLIENTS_FILE)
    q = request.args.get("q", "").lower()
    if q:
        clients = [c for c in clients
                   if q in c.get("name","").lower() or q in c.get("phone","")]
    return jsonify(clients)

@app.route("/api/clients", methods=["POST"])
def add_client():
    clients = read_json(CLIENTS_FILE)
    data    = request.json or {}
    client  = {
        "id":         str(uuid.uuid4())[:8],
        "name":       data.get("name","").strip(),
        "guardian":   data.get("guardian","").strip(),
        "phone":      data.get("phone","").strip(),
        "address":    data.get("address","").strip(),
        "id_proof":   data.get("id_proof","").strip(),
        "created_at": now_str()
    }
    if not client["name"]:
        return jsonify({"error": "Name is required"}), 400
    clients.append(client)
    write_json(CLIENTS_FILE, clients)
    return jsonify(client), 201

@app.route("/api/clients/<client_id>", methods=["GET"])
def get_client(client_id):
    client = next((c for c in read_json(CLIENTS_FILE) if c["id"] == client_id), None)
    return jsonify(client) if client else (jsonify({"error": "Not found"}), 404)

@app.route("/api/clients/<client_id>", methods=["PUT"])
def update_client(client_id):
    clients = read_json(CLIENTS_FILE)
    data    = request.json or {}
    for c in clients:
        if c["id"] == client_id:
            c.update({k: v for k, v in data.items() if k != "id"})
            write_json(CLIENTS_FILE, clients)
            return jsonify(c)
    return jsonify({"error": "Not found"}), 404

@app.route("/api/clients/<client_id>", methods=["DELETE"])
def delete_client(client_id):
    clients = [c for c in read_json(CLIENTS_FILE) if c["id"] != client_id]
    write_json(CLIENTS_FILE, clients)
    return jsonify({"ok": True})

# ══════════════════════════════════════════════════════════════════════════════
#  LOANS
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/loans", methods=["GET"])
def get_loans():
    loans    = read_json(LOANS_FILE)
    payments = read_json(PAYMENTS_FILE)
    client_id = request.args.get("client_id")
    if client_id:
        loans = [l for l in loans if l["client_id"] == client_id]

    for loan in loans:
        interest, total = calculate_interest(
            loan["amount"], loan["rate"], loan["date_taken"], loan["interest_type"]
        )
        paid = sum(float(p["amount"]) for p in payments if p["loan_id"] == loan["id"])
        loan["interest_accrued"]  = interest
        loan["total_payable"]     = total
        loan["total_paid"]        = round(paid, 2)
        loan["remaining_balance"] = round(total - paid, 2)
        loan["status"]            = "Paid" if loan["remaining_balance"] <= 0 else "Active"
    return jsonify(loans)

@app.route("/api/loans", methods=["POST"])
def add_loan():
    loans = read_json(LOANS_FILE)
    data  = request.json or {}
    loan  = {
        "id":            str(uuid.uuid4())[:8],
        "client_id":     data.get("client_id",""),
        "amount":        float(data.get("amount", 0)),
        "rate":          float(data.get("rate", 0)),
        "interest_type": data.get("interest_type", "simple"),
        "collateral":    data.get("collateral",""),
        "date_taken":    data.get("date_taken", now_str()),
        "notes":         data.get("notes",""),
        "images":        data.get("images", []),   # list of base64 strings
        "created_at":    now_str()
    }
    if not loan["client_id"] or not loan["amount"]:
        return jsonify({"error": "client_id and amount required"}), 400
    loans.append(loan)
    write_json(LOANS_FILE, loans)
    return jsonify(loan), 201

@app.route("/api/loans/<loan_id>", methods=["DELETE"])
def delete_loan(loan_id):
    write_json(LOANS_FILE, [l for l in read_json(LOANS_FILE) if l["id"] != loan_id])
    # Also delete related payments
    write_json(PAYMENTS_FILE, [p for p in read_json(PAYMENTS_FILE) if p["loan_id"] != loan_id])
    return jsonify({"ok": True})

# ══════════════════════════════════════════════════════════════════════════════
#  PAYMENTS
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/payments", methods=["GET"])
def get_payments():
    payments  = read_json(PAYMENTS_FILE)
    loan_id   = request.args.get("loan_id")
    client_id = request.args.get("client_id")
    if loan_id:
        payments = [p for p in payments if p["loan_id"] == loan_id]
    if client_id:
        loan_ids = {l["id"] for l in read_json(LOANS_FILE) if l["client_id"] == client_id}
        payments = [p for p in payments if p["loan_id"] in loan_ids]
    return jsonify(sorted(payments, key=lambda x: x["date"], reverse=True))

@app.route("/api/payments", methods=["POST"])
def add_payment():
    payments = read_json(PAYMENTS_FILE)
    data     = request.json or {}
    payment  = {
        "id":         str(uuid.uuid4())[:8],
        "loan_id":    data.get("loan_id",""),
        "amount":     float(data.get("amount", 0)),
        "date":       data.get("date", now_str()),
        "note":       data.get("note",""),
        "created_at": now_str()
    }
    if not payment["loan_id"] or not payment["amount"]:
        return jsonify({"error": "loan_id and amount required"}), 400
    payments.append(payment)
    write_json(PAYMENTS_FILE, payments)
    return jsonify(payment), 201

@app.route("/api/payments/<payment_id>", methods=["DELETE"])
def delete_payment(payment_id):
    write_json(PAYMENTS_FILE, [p for p in read_json(PAYMENTS_FILE) if p["id"] != payment_id])
    return jsonify({"ok": True})

# ══════════════════════════════════════════════════════════════════════════════
#  PURCHASES
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/purchases", methods=["GET"])
def get_purchases():
    purchases = read_json(PURCHASES_FILE)
    client_id = request.args.get("client_id")
    if client_id:
        purchases = [p for p in purchases if p["client_id"] == client_id]
    today = now_str()
    for p in purchases:
        remaining  = round(float(p["price"]) - float(p.get("amount_paid", 0)), 2)
        p["remaining"] = remaining
        if remaining <= 0:
            p["status"] = "Paid"
        elif p.get("due_date") and p["due_date"] < today:
            p["status"] = "Overdue"
        else:
            p["status"] = "Pending"
    return jsonify(purchases)

@app.route("/api/purchases", methods=["POST"])
def add_purchase():
    purchases = read_json(PURCHASES_FILE)
    data      = request.json or {}
    purchase  = {
        "id":            str(uuid.uuid4())[:8],
        "client_id":     data.get("client_id",""),
        "product":       data.get("product",""),
        "price":         float(data.get("price", 0)),
        "amount_paid":   float(data.get("amount_paid", 0)),
        "purchase_date": data.get("purchase_date", now_str()),
        "due_date":      data.get("due_date",""),
        "notes":         data.get("notes",""),
        "images":        data.get("images", []),   # list of base64 strings
        "created_at":    now_str()
    }
    if not purchase["client_id"] or not purchase["product"]:
        return jsonify({"error": "client_id and product required"}), 400
    purchases.append(purchase)
    write_json(PURCHASES_FILE, purchases)
    return jsonify(purchase), 201

@app.route("/api/purchases/<purchase_id>", methods=["PUT"])
def update_purchase(purchase_id):
    purchases = read_json(PURCHASES_FILE)
    data      = request.json or {}
    for p in purchases:
        if p["id"] == purchase_id:
            if "add_payment" in data:
                p["amount_paid"] = round(float(p.get("amount_paid",0)) + float(data["add_payment"]), 2)
            if "due_date" in data:
                p["due_date"] = data["due_date"]
            write_json(PURCHASES_FILE, purchases)
            return jsonify(p)
    return jsonify({"error": "Not found"}), 404

@app.route("/api/purchases/<purchase_id>", methods=["DELETE"])
def delete_purchase(purchase_id):
    write_json(PURCHASES_FILE, [p for p in read_json(PURCHASES_FILE) if p["id"] != purchase_id])
    return jsonify({"ok": True})

# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    clients   = read_json(CLIENTS_FILE)
    loans     = read_json(LOANS_FILE)
    payments  = read_json(PAYMENTS_FILE)
    purchases = read_json(PURCHASES_FILE)
    today     = now_str()

    total_principal  = sum(float(l["amount"]) for l in loans)
    total_collected  = sum(float(p["amount"]) for p in payments)
    loan_outstanding = 0

    for loan in loans:
        _, total = calculate_interest(loan["amount"], loan["rate"], loan["date_taken"], loan["interest_type"])
        paid     = sum(float(p["amount"]) for p in payments if p["loan_id"] == loan["id"])
        rem      = total - paid
        if rem > 0:
            loan_outstanding += rem

    purch_outstanding = 0
    purch_overdue     = 0
    for p in purchases:
        rem = float(p["price"]) - float(p.get("amount_paid", 0))
        if rem > 0:
            purch_outstanding += rem
            if p.get("due_date") and p["due_date"] < today:
                purch_overdue += 1

    return jsonify({
        "total_clients":       len(clients),
        "total_loans":         len(loans),
        "total_loan_principal": round(total_principal, 2),
        "total_collected":     round(total_collected, 2),
        "total_outstanding":   round(loan_outstanding, 2),
        "total_purchases":     len(purchases),
        "purchase_outstanding": round(purch_outstanding, 2),
        "purchase_overdue_count": purch_overdue
    })

# ══════════════════════════════════════════════════════════════════════════════
#  CLIENT HISTORY
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/clients/<client_id>/history", methods=["GET"])
def client_history(client_id):
    clients   = read_json(CLIENTS_FILE)
    client    = next((c for c in clients if c["id"] == client_id), None)
    if not client:
        return jsonify({"error": "Not found"}), 404

    loans     = [l for l in read_json(LOANS_FILE)     if l["client_id"] == client_id]
    payments  = read_json(PAYMENTS_FILE)
    purchases = [p for p in read_json(PURCHASES_FILE) if p["client_id"] == client_id]
    today     = now_str()
    timeline  = []
    loan_out  = 0

    for loan in loans:
        interest, total = calculate_interest(
            loan["amount"], loan["rate"], loan["date_taken"], loan["interest_type"])
        paid    = sum(float(p["amount"]) for p in payments if p["loan_id"] == loan["id"])
        rem     = round(total - paid, 2)
        loan_out += max(0, rem)
        loan.update({
            "interest_accrued":  interest,
            "total_payable":     total,
            "total_paid":        round(paid, 2),
            "remaining_balance": rem,
            "status":            "Paid" if rem <= 0 else "Active",
            "payments":          sorted([p for p in payments if p["loan_id"] == loan["id"]],
                                        key=lambda x: x["date"])
        })
        timeline.append({"date": loan["date_taken"], "type": "loan", "data": loan})

    purch_out = 0
    for p in purchases:
        rem = round(float(p["price"]) - float(p.get("amount_paid", 0)), 2)
        p["remaining"] = rem
        if rem <= 0:            p["status"] = "Paid"
        elif p.get("due_date") and p["due_date"] < today: p["status"] = "Overdue"
        else:                   p["status"] = "Pending"
        purch_out += max(0, rem)
        timeline.append({"date": p["purchase_date"], "type": "purchase", "data": p})

    timeline.sort(key=lambda x: x["date"], reverse=True)

    return jsonify({
        "client":    client,
        "loans":     loans,
        "purchases": purchases,
        "timeline":  timeline,
        "summary": {
            "total_loan_outstanding":     round(loan_out, 2),
            "total_purchase_outstanding": round(purch_out, 2),
            "grand_outstanding":          round(loan_out + purch_out, 2)
        }
    })

# ══════════════════════════════════════════════════════════════════════════════
#  BACKUP — download all data as ZIP
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/backup", methods=["GET"])
def backup():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in ["clients.json", "loans.json", "payments.json", "purchases.json"]:
            fpath = os.path.join(DATA_DIR, fname)
            if os.path.exists(fpath):
                zf.write(fpath, fname)
    buf.seek(0)
    return send_file(
        buf, mimetype="application/zip",
        as_attachment=True,
        download_name=f"financedesk_backup_{now_str()}.zip"
    )

# ══════════════════════════════════════════════════════════════════════════════
#  SEED SAMPLE DATA (only runs if data folder is empty)
# ══════════════════════════════════════════════════════════════════════════════
def seed_data():
    if read_json(CLIENTS_FILE):
        return  # already has data — don't overwrite
    write_json(CLIENTS_FILE, [
        {"id":"c001","name":"Ravi Kumar","guardian":"Ramesh Kumar","phone":"9876543210","address":"12 MG Road, Delhi","id_proof":"Aadhaar 1234","created_at":"2024-01-10"},
        {"id":"c002","name":"Priya Sharma","guardian":"Suresh Sharma","phone":"9123456780","address":"45 Nehru Street, Mumbai","id_proof":"PAN ABCDE1234F","created_at":"2024-02-15"},
        {"id":"c003","name":"Anil Mehta","guardian":"Vijay Mehta","phone":"9988776655","address":"7 Gandhi Nagar, Jaipur","id_proof":"","created_at":"2024-03-01"},
    ])
    write_json(LOANS_FILE, [
        {"id":"l001","client_id":"c001","amount":50000,"rate":2,"interest_type":"simple","collateral":"Gold ring 10g","date_taken":"2024-01-15","notes":"Emergency loan","images":[],"created_at":"2024-01-15"},
        {"id":"l002","client_id":"c002","amount":25000,"rate":18,"interest_type":"compound","collateral":"Silver jewellery set","date_taken":"2024-03-10","notes":"","images":[],"created_at":"2024-03-10"},
        {"id":"l003","client_id":"c003","amount":10000,"rate":3,"interest_type":"simple","collateral":"Bike RC book","date_taken":"2023-11-01","notes":"Small personal loan","images":[],"created_at":"2023-11-01"},
    ])
    write_json(PAYMENTS_FILE, [
        {"id":"p001","loan_id":"l001","amount":10000,"date":"2024-02-01","note":"First instalment","created_at":"2024-02-01"},
        {"id":"p002","loan_id":"l001","amount":15000,"date":"2024-04-01","note":"Second instalment","created_at":"2024-04-01"},
        {"id":"p003","loan_id":"l003","amount":5000,"date":"2023-12-15","note":"Partial repayment","created_at":"2023-12-15"},
    ])
    write_json(PURCHASES_FILE, [
        {"id":"pu001","client_id":"c001","product":"Samsung TV 43\"","price":35000,"amount_paid":10000,"purchase_date":"2024-02-10","due_date":"2024-08-10","notes":"","images":[],"created_at":"2024-02-10"},
        {"id":"pu002","client_id":"c002","product":"Refrigerator LG","price":20000,"amount_paid":20000,"purchase_date":"2024-01-20","due_date":"2024-06-20","notes":"Fully paid","images":[],"created_at":"2024-01-20"},
        {"id":"pu003","client_id":"c003","product":"Washing Machine","price":15000,"amount_paid":3000,"purchase_date":"2023-10-05","due_date":"2024-01-05","notes":"","images":[],"created_at":"2023-10-05"},
    ])

# ── Run seed on startup (works for both gunicorn and python app.py) ──────────
seed_data()

# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
