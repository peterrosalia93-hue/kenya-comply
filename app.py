# KenyaComply Web App
# Flask app for Kenyan Business Compliance
# Features: ETIMS Invoices, Tax Calculator, Tax Returns, iTax Integration, M-Pesa Payments

from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import json
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kenyacomply-dev-secret-key')

# Import our modules
from etims_invoice import create_standard_invoice
from tax_calculator import calculate_paye, calculate_vat
from mpesa import (
    initiate_mpesa_payment, verify_mpesa_payment,
    process_mpesa_callback, PAYMENT_CONFIG
)

# In-memory stores (replace with DB in production)
USERS = {}
TAX_RETURNS = {}

# ============================================
# AUTH ROUTES
# ============================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '')
        name = request.form.get('name', '')
        kra_pin = request.form.get('kra_pin', '')
        if email:
            if email not in USERS:
                USERS[email] = {
                    'id': str(uuid.uuid4()), 'email': email, 'name': name,
                    'kra_pin': kra_pin, 'invoices': [], 'tax_returns': []
                }
            else:
                if kra_pin:
                    USERS[email]['kra_pin'] = kra_pin
            session['user_id'] = USERS[email]['id']
            session['email'] = email
            return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ============================================
# MAIN PAGES
# ============================================

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = next((u for u in USERS.values() if u['id'] == session['user_id']), None)
    invoices = user['invoices'] if user else []
    returns = user.get('tax_returns', []) if user else []
    return render_template_string(DASHBOARD_HTML, user=user, invoices=invoices, returns=returns)

@app.route("/tax-returns")
def tax_returns_page():
    return render_template_string(TAX_RETURNS_HTML)

@app.route("/itax-guide")
def itax_guide():
    return render_template_string(ITAX_GUIDE_HTML)

@app.route("/print/<invoice_number>")
def print_invoice(invoice_number):
    invoice_data = None
    for user in USERS.values():
        for inv in user.get('invoices', []):
            if inv['number'] == invoice_number:
                invoice_data = inv
                break
    if not invoice_data:
        return "Invoice not found", 404
    return render_template_string(PRINT_HTML,
        invoice_number=invoice_data['number'],
        date=invoice_data['date'],
        seller_name=invoice_data.get('seller', 'N/A'),
        seller_pin='P000000000',
        buyer_name=invoice_data['buyer'],
        buyer_pin='P000000000',
        subtotal=invoice_data['amount'] / 1.16,
        vat=invoice_data['amount'] * 0.16 / 1.16,
        total=invoice_data['amount']
    )

@app.route("/health")
def health():
    return {"status": "ok", "service": "kenya-comply", "version": "2.0"}

# ============================================
# API ROUTES
# ============================================

@app.route("/api/payment/initiate", methods=["POST"])
def api_payment_initiate():
    data = request.json
    phone = data.get('phone', '')
    amount = data.get('amount', PAYMENT_CONFIG['fee'])
    account_ref = data.get('account_ref', 'KenyaComply')
    result = initiate_mpesa_payment(phone, amount, account_ref)
    return jsonify(result)

@app.route("/api/payment/verify/<tx_ref>", methods=["GET"])
def api_payment_verify(tx_ref):
    result = verify_mpesa_payment(tx_ref)
    return jsonify(result)

@app.route("/api/mpesa/callback", methods=["POST"])
def api_mpesa_callback():
    callback_data = request.json
    result = process_mpesa_callback(callback_data)
    return jsonify(result)

@app.route("/api/invoice", methods=["POST"])
def api_invoice():
    data = request.json
    invoice = create_standard_invoice(
        seller_name=data["seller_name"],
        seller_pin=data["seller_pin"],
        seller_address="Nairobi, Kenya",
        seller_phone="+254700000000",
        buyer_name=data["buyer_name"],
        buyer_pin=data["buyer_pin"],
        buyer_address="Kenya",
        items=[{"description": "Service", "quantity": 1, "unit_price": data["amount"], "vat_rate": 16}]
    )
    invoice_text = f"""KENYACOMPLY ETIMS INVOICE
========================
Invoice Number: {invoice.invoice_number}
Date: {invoice.date}

SELLER: {data['seller_name']} | KRA PIN: {data['seller_pin']}
BUYER: {data['buyer_name']} | KRA PIN: {data['buyer_pin']}

ITEMS:
Description     | Qty | Unit Price     | VAT  | Total
Service         |  1  | {data['amount']:,.2f}  | 16%  | {invoice.grand_total:,.2f}

Subtotal: KES {invoice.subtotal:,.2f}
VAT (16%): KES {invoice.total_vat:,.2f}
GRAND TOTAL: KES {invoice.grand_total:,.2f}

Generated by KenyaComply - kenya-comply.vercel.app
"""
    if 'user_id' in session:
        user = next((u for u in USERS.values() if u['id'] == session['user_id']), None)
        if user:
            user['invoices'].append({
                'number': invoice.invoice_number, 'amount': invoice.grand_total,
                'buyer': data["buyer_name"], 'date': invoice.date, 'seller': data["seller_name"]
            })
    return jsonify({
        "invoice_number": invoice.invoice_number, "date": invoice.date,
        "subtotal": invoice.subtotal, "vat": invoice.total_vat,
        "total": invoice.grand_total, "download_text": invoice_text
    })

@app.route("/api/paye", methods=["POST"])
def api_paye():
    data = request.json
    result = calculate_paye(data["salary"])
    return jsonify(result.to_dict())

@app.route("/api/vat", methods=["POST"])
def api_vat():
    data = request.json
    result = calculate_vat(data["sales"], data.get("exempt", 0), data.get("input_vat", 0))
    return jsonify({
        "gross_sales": result.gross_sales, "vat_exempt": result.vat_exempt,
        "vat_collected": result.vat_collected, "input_vat": result.input_vat,
        "net_vat_payable": result.net_vat_payable
    })

@app.route("/api/tax-return", methods=["POST"])
def api_tax_return():
    """Generate tax return data for filing on iTax."""
    data = request.json
    return_type = data.get("return_type", "income_tax")
    ref = f"TR_{uuid.uuid4().hex[:10].upper()}"

    if return_type == "paye":
        # Employer monthly PAYE return
        employees = data.get("employees", [])
        total_paye = 0
        employee_details = []
        for emp in employees:
            result = calculate_paye(float(emp.get("gross", 0)))
            total_paye += result.tax_after_relief
            employee_details.append({
                "name": emp.get("name", ""),
                "pin": emp.get("pin", ""),
                "gross": result.gross_salary,
                "nssf": result.nssf,
                "nhif": result.nhif,
                "paye": result.tax_after_relief,
                "net": result.net_salary
            })
        return jsonify({
            "status": "success", "ref": ref, "return_type": "PAYE (P10)",
            "period": data.get("period", datetime.now().strftime("%B %Y")),
            "total_employees": len(employees), "total_paye": round(total_paye, 2),
            "employees": employee_details,
            "filing_steps": [
                "Login to iTax at itax.kra.go.ke",
                "Go to Returns > File Return > PAYE",
                "Select the tax period",
                "Upload CSV or fill P10 form with the data below",
                "Submit and pay via M-Pesa or bank"
            ],
            "itax_url": "https://itax.kra.go.ke/KRA-Portal/eReturn/returnPeriod.htm?actionCode=loadPage&ESSION_TYPE=RETURNS_R"
        })

    elif return_type == "vat":
        vat_result = calculate_vat(
            float(data.get("output_sales", 0)),
            float(data.get("exempt_sales", 0)),
            float(data.get("input_vat", 0))
        )
        return jsonify({
            "status": "success", "ref": ref, "return_type": "VAT Return",
            "period": data.get("period", datetime.now().strftime("%B %Y")),
            "output_sales": vat_result.gross_sales,
            "exempt_sales": vat_result.vat_exempt,
            "vat_collected": round(vat_result.vat_collected, 2),
            "input_vat": vat_result.input_vat,
            "net_vat_payable": round(vat_result.net_vat_payable, 2),
            "filing_steps": [
                "Login to iTax at itax.kra.go.ke",
                "Go to Returns > File Return > VAT",
                "Select the tax period",
                "Enter output sales and input VAT details",
                "Submit and pay VAT due via M-Pesa or bank",
                "Keep records for 5 years"
            ],
            "itax_url": "https://itax.kra.go.ke/KRA-Portal/eReturn/returnPeriod.htm?actionCode=loadPage&SESSION_TYPE=RETURNS_V"
        })

    else:
        # Individual Income Tax Return
        gross_annual = float(data.get("annual_income", 0))
        monthly = gross_annual / 12
        result = calculate_paye(monthly)
        annual_tax = result.tax_after_relief * 12
        annual_nssf = result.nssf * 12
        annual_nhif = result.nhif * 12

        other_income = float(data.get("other_income", 0))
        deductions = float(data.get("deductions", 0))
        withholding_tax = float(data.get("withholding_tax", 0))
        paye_paid = float(data.get("paye_already_paid", annual_tax))

        total_income = gross_annual + other_income
        taxable = total_income - annual_nssf - deductions
        # Recalculate on total
        monthly_taxable = taxable / 12
        recalc = calculate_paye(monthly_taxable + (result.nssf))  # add back NSSF since calc deducts it
        final_tax = recalc.tax_after_relief * 12
        tax_balance = final_tax - paye_paid - withholding_tax

        return jsonify({
            "status": "success", "ref": ref, "return_type": "Income Tax (IT1)",
            "tax_year": data.get("tax_year", str(datetime.now().year - 1)),
            "employment_income": gross_annual,
            "other_income": other_income,
            "total_income": total_income,
            "nssf_deduction": round(annual_nssf, 2),
            "other_deductions": deductions,
            "taxable_income": round(taxable, 2),
            "tax_charged": round(final_tax, 2),
            "personal_relief": 28800,
            "paye_already_paid": paye_paid,
            "withholding_tax": withholding_tax,
            "tax_balance": round(tax_balance, 2),
            "refund_or_payable": "REFUND" if tax_balance < 0 else "PAYABLE",
            "filing_steps": [
                "Login to iTax at itax.kra.go.ke",
                "Go to Returns > File Return > Income Tax - Resident Individual",
                "Select tax year and fill in employment income",
                "Add other income sources (rental, business, interest)",
                "Enter allowable deductions (NSSF, insurance, mortgage)",
                "Review computed tax and submit",
                "Pay any balance due or request refund"
            ],
            "itax_url": "https://itax.kra.go.ke/KRA-Portal/eReturn/returnPeriod.htm?actionCode=loadPage&RETURN_TYPE=IT1",
            "deadline": "30th June" if data.get("tax_year") else "30th June annually"
        })

# ============================================
# HTML TEMPLATES
# ============================================

PRINT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Invoice - KenyaComply</title>
    <style>
        body { font-family: 'Courier New', monospace; margin: 40px; max-width: 800px; }
        .invoice { border: 2px solid #000; padding: 30px; }
        h1 { text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; }
        .row { display: flex; justify-content: space-between; margin: 10px 0; }
        .section { margin: 20px 0; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #000; padding: 10px; text-align: left; }
        th { background: #f0f0f0; }
        .total { font-size: 1.3em; font-weight: bold; }
        .print-btn { background: #1a1a2e; color: white; padding: 15px 30px; border: none; cursor: pointer; font-size: 1rem; }
        @media print { .print-btn { display: none; } }
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">Print Invoice</button>
    <div class="invoice">
        <h1>KENYACOMPLY - ETIMS INVOICE</h1>
        <div class="section">
            <div class="row"><strong>Invoice Number:</strong> <span>{{invoice_number}}</span></div>
            <div class="row"><strong>Date:</strong> <span>{{date}}</span></div>
        </div>
        <div class="section"><h3>SELLER</h3><div>{{seller_name}}</div><div>KRA PIN: {{seller_pin}}</div></div>
        <div class="section"><h3>BUYER</h3><div>{{buyer_name}}</div><div>KRA PIN: {{buyer_pin}}</div></div>
        <table>
            <tr><th>Description</th><th>Qty</th><th>Unit Price</th><th>VAT</th><th>Total</th></tr>
            <tr><td>Service</td><td>1</td><td>KES {{subtotal}}</td><td>16%</td><td>KES {{total}}</td></tr>
        </table>
        <div class="section total">
            <div class="row"><span>Subtotal:</span> <span>KES {{subtotal}}</span></div>
            <div class="row"><span>VAT (16%):</span> <span>KES {{vat}}</span></div>
            <div class="row"><span>GRAND TOTAL:</span> <span>KES {{total}}</span></div>
        </div>
        <p style="text-align: center; margin-top: 30px;">Generated by KenyaComply | kenya-comply.vercel.app</p>
    </div>
</body>
</html>
"""

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - KenyaComply</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
        .card { background: white; padding: 40px; border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); width: 100%; max-width: 420px; }
        h1 { color: #1a1a2e; margin-bottom: 5px; text-align: center; }
        .subtitle { color: #666; text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: 600; color: #333; }
        input { width: 100%; padding: 14px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 1rem; box-sizing: border-box; }
        input:focus { outline: none; border-color: #1a1a2e; }
        button { background: #1a1a2e; color: white; padding: 16px; border: none; border-radius: 8px; font-size: 1rem; width: 100%; cursor: pointer; font-weight: 600; }
        button:hover { background: #16213e; }
        .back { display: block; text-align: center; margin-top: 20px; color: #666; text-decoration: none; }
        .hint { font-size: 0.85rem; color: #999; margin-top: 4px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>KenyaComply</h1>
        <p class="subtitle">Sign in to manage your tax compliance</p>
        <form method="POST">
            <div class="form-group">
                <label>Email</label>
                <input type="email" name="email" required placeholder="you@company.co.ke">
            </div>
            <div class="form-group">
                <label>Your Name</label>
                <input type="text" name="name" required placeholder="John Doe">
            </div>
            <div class="form-group">
                <label>KRA PIN (Optional)</label>
                <input type="text" name="kra_pin" placeholder="A123456789B" pattern="[A-Z][0-9]{9}[A-Z]">
                <div class="hint">Format: A123456789B - needed for tax returns</div>
            </div>
            <button type="submit">Continue</button>
        </form>
        <a href="/" class="back">Back to home</a>
    </div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - KenyaComply</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; margin: 0; }
        header { background: #1a1a2e; color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; }
        .logo { font-size: 1.5rem; font-weight: bold; }
        .container { max-width: 960px; margin: 30px auto; padding: 0 20px; }
        .card { background: white; padding: 25px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { color: #1a1a2e; margin: 0 0 20px 0; }
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; }
        .stat { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }
        .stat-value { font-size: 1.8rem; font-weight: bold; color: #1a1a2e; }
        .stat-label { color: #666; font-size: 0.9rem; }
        .invoice { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #1a1a2e; }
        .invoice-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
        .invoice-number { font-weight: bold; color: #1a1a2e; }
        .invoice-amount { font-size: 1.2rem; font-weight: bold; color: #2e7d32; }
        .invoice-date { color: #666; font-size: 0.9rem; }
        .btn { display: inline-block; background: #1a1a2e; color: white; padding: 12px 20px; border-radius: 8px; text-decoration: none; font-weight: 600; border: none; cursor: pointer; font-size: 0.95rem; }
        .btn:hover { background: #16213e; }
        .btn-green { background: #2e7d32; }
        .btn-green:hover { background: #1b5e20; }
        .btn-blue { background: #1565c0; }
        .btn-blue:hover { background: #0d47a1; }
        .btn-outline { background: transparent; border: 2px solid #1a1a2e; color: #1a1a2e; }
        .actions { display: flex; gap: 10px; flex-wrap: wrap; }
        .return-item { background: #e8f5e9; padding: 12px 15px; border-radius: 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
        .return-type { font-weight: 600; color: #2e7d32; }
        .return-ref { color: #666; font-size: 0.85rem; }
        .kra-pin { background: #fff3cd; padding: 8px 15px; border-radius: 8px; margin-bottom: 15px; font-size: 0.9rem; }
    </style>
</head>
<body>
    <header>
        <div class="logo">KenyaComply</div>
        <div>
            <a href="/" style="color: white; text-decoration: none; margin-right: 20px;">Home</a>
            <a href="/logout" style="color: white; text-decoration: none;">Logout</a>
        </div>
    </header>
    <div class="container">
        <div class="card">
            <h2>Welcome back, {{ user.name }}</h2>
            {% if user.kra_pin %}
                <div class="kra-pin">KRA PIN: <strong>{{ user.kra_pin }}</strong></div>
            {% else %}
                <div class="kra-pin">No KRA PIN saved. <a href="/login">Update your profile</a> to enable tax return features.</div>
            {% endif %}
        </div>

        <div class="card">
            <h2>Quick Stats</h2>
            <div class="stat-grid">
                <div class="stat">
                    <div class="stat-value">{{ invoices|length }}</div>
                    <div class="stat-label">Invoices</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{{ returns|length }}</div>
                    <div class="stat-label">Tax Returns</div>
                </div>
                <div class="stat">
                    <div class="stat-value">KES {{ "{:,.0f}".format(invoices|sum(attribute='amount')) if invoices else '0' }}</div>
                    <div class="stat-label">Total Billed</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Quick Actions</h2>
            <div class="actions">
                <a href="/" class="btn">New Invoice</a>
                <a href="/tax-returns" class="btn btn-green">File Tax Return</a>
                <a href="/itax-guide" class="btn btn-blue">iTax Guide</a>
                <a href="/" class="btn btn-outline">PAYE Calculator</a>
                <a href="/" class="btn btn-outline">VAT Calculator</a>
            </div>
        </div>

        <div class="card">
            <h2>Recent Invoices</h2>
            {% if invoices %}
                {% for inv in invoices|reverse %}
                <div class="invoice">
                    <div class="invoice-header">
                        <span class="invoice-number">{{ inv.number }}</span>
                        <span class="invoice-amount">KES {{ "{:,.0f}".format(inv.amount) }}</span>
                    </div>
                    <div class="invoice-date">{{ inv.buyer }} | {{ inv.date }}</div>
                </div>
                {% endfor %}
            {% else %}
                <p style="color: #666;">No invoices yet. Create your first one!</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

# ============================================
# MAIN APP HTML (Tabs: Invoice, PAYE, VAT, M-Pesa, Tax Returns)
# ============================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KenyaComply - Tax Compliance & M-Pesa Payments</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }
        .container { max-width: 860px; margin: 0 auto; padding: 20px; }
        header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 40px 20px; text-align: center; border-radius: 12px; margin-bottom: 30px; }
        h1 { font-size: 2.2rem; margin-bottom: 8px; }
        .subtitle { opacity: 0.85; font-size: 1.05rem; }
        .badges { margin-top: 15px; }
        .badge { display: inline-block; background: rgba(255,255,255,0.15); color: white; padding: 5px 14px; border-radius: 20px; font-size: 0.85rem; margin: 3px; }
        .nav { display: flex; justify-content: center; gap: 12px; margin-top: 20px; flex-wrap: wrap; }
        .nav-link { color: white; text-decoration: none; padding: 8px 18px; border-radius: 20px; background: rgba(255,255,255,0.12); font-size: 0.95rem; }
        .nav-link:hover { background: rgba(255,255,255,0.25); }
        .tabs { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
        .tab { padding: 12px 20px; background: white; border: none; border-radius: 8px; cursor: pointer; font-size: 0.95rem; transition: all 0.2s; box-shadow: 0 2px 5px rgba(0,0,0,0.08); }
        .tab:hover { transform: translateY(-1px); }
        .tab.active { background: #1a1a2e; color: white; }
        .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); margin-bottom: 20px; }
        .form-group { margin-bottom: 18px; }
        label { display: block; margin-bottom: 6px; font-weight: 600; font-size: 0.95rem; }
        input, select, textarea { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 1rem; transition: border-color 0.2s; box-sizing: border-box; }
        input:focus, select:focus, textarea:focus { outline: none; border-color: #1a1a2e; }
        .row { display: flex; gap: 15px; flex-wrap: wrap; }
        .col { flex: 1; min-width: 200px; }
        button.primary { background: #1a1a2e; color: white; padding: 15px 30px; border: none; border-radius: 8px; font-size: 1.05rem; cursor: pointer; width: 100%; transition: all 0.2s; font-weight: 600; }
        button.primary:hover { background: #16213e; }
        button.mpesa-btn { background: #4CAF50; }
        button.mpesa-btn:hover { background: #388E3C; }
        .result { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #1a1a2e; }
        .result h3 { margin-bottom: 12px; color: #1a1a2e; }
        .result-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e0e0e0; }
        .result-row:last-child { border-bottom: none; font-weight: bold; font-size: 1.15rem; }
        .btn-row { display: flex; gap: 10px; margin-top: 15px; flex-wrap: wrap; }
        .download-btn { background: #2e7d32; color: white; padding: 12px 20px; border: none; border-radius: 8px; font-size: 0.95rem; cursor: pointer; font-weight: 600; }
        .print-btn { background: #1565c0; color: white; padding: 12px 20px; border: none; border-radius: 8px; font-size: 0.95rem; cursor: pointer; font-weight: 600; }
        .payment-notice { background: #fff3cd; color: #856404; padding: 15px; border-radius: 8px; margin-bottom: 15px; font-weight: 600; text-align: center; }
        .payment-status { background: #d4edda; color: #155724; padding: 12px; border-radius: 8px; margin: 15px 0; text-align: center; font-weight: 600; }
        .payment-error { background: #f8d7da; color: #721c24; padding: 12px; border-radius: 8px; margin: 15px 0; text-align: center; font-weight: 600; }
        .mpesa-info { background: #e8f5e9; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #4CAF50; }
        .mpesa-info h4 { color: #2e7d32; margin-bottom: 5px; }
        .itax-link { background: #e3f2fd; padding: 15px; border-radius: 8px; margin-top: 15px; text-align: center; }
        .itax-link a { color: #1565c0; font-weight: 600; text-decoration: none; font-size: 1.05rem; }
        .itax-link a:hover { text-decoration: underline; }
        .steps { counter-reset: step; list-style: none; padding: 0; }
        .steps li { counter-increment: step; padding: 8px 0 8px 35px; position: relative; border-bottom: 1px solid #f0f0f0; }
        .steps li::before { content: counter(step); position: absolute; left: 0; background: #1a1a2e; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.8rem; font-weight: bold; }
        .hidden { display: none; }
        footer { text-align: center; padding: 20px; opacity: 0.6; font-size: 0.9rem; }
        @media (max-width: 600px) { .container { padding: 10px; } .card { padding: 20px; } h1 { font-size: 1.8rem; } .tabs { gap: 5px; } .tab { padding: 10px 14px; font-size: 0.85rem; } }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>KenyaComply</h1>
            <p class="subtitle">Tax Compliance, M-Pesa Payments & iTax Filing</p>
            <div class="badges">
                <span class="badge">ETIMS Invoices</span>
                <span class="badge">M-Pesa STK Push</span>
                <span class="badge">Tax Returns</span>
                <span class="badge">KRA iTax</span>
            </div>
            <div class="nav">
                <a href="/login" class="nav-link">Login</a>
                <a href="/dashboard" class="nav-link">Dashboard</a>
                <a href="/tax-returns" class="nav-link">Tax Returns</a>
                <a href="/itax-guide" class="nav-link">iTax Guide</a>
            </div>
        </header>

        <div class="tabs">
            <button class="tab active" onclick="showTab('invoice')">Invoice</button>
            <button class="tab" onclick="showTab('paye')">PAYE</button>
            <button class="tab" onclick="showTab('vat')">VAT</button>
            <button class="tab" onclick="showTab('mpesa')">M-Pesa Pay</button>
        </div>

        <!-- Invoice Tab -->
        <div id="invoice" class="card">
            <h2>Generate ETIMS Invoice</h2>
            <form id="invoiceForm">
                <div class="row">
                    <div class="col form-group">
                        <label>Seller Name</label>
                        <input type="text" name="seller_name" placeholder="Your Company Ltd" required>
                    </div>
                    <div class="col form-group">
                        <label>Seller KRA PIN</label>
                        <input type="text" name="seller_pin" placeholder="P051234567A" required>
                    </div>
                </div>
                <div class="row">
                    <div class="col form-group">
                        <label>Buyer Name</label>
                        <input type="text" name="buyer_name" placeholder="Client Company Ltd" required>
                    </div>
                    <div class="col form-group">
                        <label>Buyer KRA PIN</label>
                        <input type="text" name="buyer_pin" placeholder="P098765432B" required>
                    </div>
                </div>
                <div class="form-group">
                    <label>Amount (KES)</label>
                    <input type="number" name="amount" placeholder="50000" required min="1">
                </div>
                <div class="form-group">
                    <label>Phone (M-Pesa Payment)</label>
                    <input type="tel" name="phone" placeholder="07XX XXX XXX" required>
                </div>
                <button type="submit" class="primary mpesa-btn">Pay KES 50 via M-Pesa & Generate Invoice</button>
            </form>
            <div id="invoiceResult" class="result hidden"></div>
        </div>

        <!-- PAYE Tab -->
        <div id="paye" class="card hidden">
            <h2>PAYE Tax Calculator (2024 Rates)</h2>
            <p style="color:#666; margin-bottom:15px;">Calculate your Pay As You Earn tax based on current KRA rates.</p>
            <form id="payeForm">
                <div class="form-group">
                    <label>Gross Monthly Salary (KES)</label>
                    <input type="number" name="salary" placeholder="100000" required min="1">
                </div>
                <button type="submit" class="primary">Calculate PAYE</button>
            </form>
            <div id="payeResult" class="result hidden"></div>
        </div>

        <!-- VAT Tab -->
        <div id="vat" class="card hidden">
            <h2>VAT Calculator</h2>
            <p style="color:#666; margin-bottom:15px;">Calculate your VAT liability (16% standard rate).</p>
            <form id="vatForm">
                <div class="form-group">
                    <label>Output Sales (KES)</label>
                    <input type="number" name="sales" placeholder="100000" required min="0">
                </div>
                <div class="row">
                    <div class="col form-group">
                        <label>Exempt Sales (KES)</label>
                        <input type="number" name="exempt" placeholder="0" value="0">
                    </div>
                    <div class="col form-group">
                        <label>Input VAT (KES)</label>
                        <input type="number" name="input_vat" placeholder="0" value="0">
                    </div>
                </div>
                <button type="submit" class="primary">Calculate VAT</button>
            </form>
            <div id="vatResult" class="result hidden"></div>
        </div>

        <!-- M-Pesa Direct Pay Tab -->
        <div id="mpesa" class="card hidden">
            <h2>M-Pesa Payment (Lipa Na M-Pesa)</h2>
            <div class="mpesa-info">
                <h4>Safaricom STK Push</h4>
                <p>Enter your phone number and amount. You'll receive an M-Pesa prompt on your phone to enter your PIN.</p>
            </div>
            <form id="mpesaForm">
                <div class="form-group">
                    <label>M-Pesa Phone Number</label>
                    <input type="tel" name="phone" placeholder="0712 345 678" required>
                </div>
                <div class="form-group">
                    <label>Amount (KES)</label>
                    <input type="number" name="amount" placeholder="1000" required min="1">
                </div>
                <div class="form-group">
                    <label>Payment Reference</label>
                    <input type="text" name="account_ref" placeholder="Invoice or Account Number" value="KenyaComply">
                </div>
                <button type="submit" class="primary mpesa-btn">Send M-Pesa STK Push</button>
            </form>
            <div id="mpesaResult" class="result hidden"></div>
        </div>

        <footer>
            <p>KenyaComply v2.0 | Built by Mwakulomba | <a href="/itax-guide" style="color:#666;">iTax Filing Guide</a></p>
        </footer>
    </div>

    <script>
        function showTab(tabId) {
            document.querySelectorAll('.card').forEach(c => c.classList.add('hidden'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById(tabId).classList.remove('hidden');
            event.target.classList.add('active');
        }

        function fmt(n) { return 'KES ' + Math.round(n).toLocaleString(); }

        function downloadInvoice(filename, text) {
            const blob = new Blob([text], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = filename + '.txt';
            document.body.appendChild(a); a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }

        // Invoice form with M-Pesa payment
        document.getElementById('invoiceForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const fd = new FormData(e.target);
            const data = Object.fromEntries(fd);
            data.amount = parseFloat(data.amount);
            const phone = data.phone;
            if (!phone || phone.replace(/\\s/g,'').length < 10) {
                alert('Please enter a valid M-Pesa phone number'); return;
            }
            const r = document.getElementById('invoiceResult');
            r.innerHTML = '<div class="payment-notice">Initiating M-Pesa payment...</div>';
            r.classList.remove('hidden');

            try {
                const payResp = await fetch('/api/payment/initiate', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({phone: phone, amount: 50})
                });
                const payResult = await payResp.json();

                if (payResult.status === 'success') {
                    const txRef = payResult.data.tx_ref;
                    r.innerHTML = '<div class="payment-status">STK Push sent! Check your phone for M-Pesa prompt.</div>';

                    // Poll for payment confirmation
                    let confirmed = payResult.data.demo;
                    if (!confirmed) {
                        r.innerHTML += '<div class="payment-notice">Waiting for payment confirmation...</div>';
                        for (let i = 0; i < 6; i++) {
                            await new Promise(resolve => setTimeout(resolve, 5000));
                            const vResp = await fetch('/api/payment/verify/' + txRef);
                            const vResult = await vResp.json();
                            if (vResult.status === 'success') { confirmed = true; break; }
                            if (vResult.status === 'cancelled' || vResult.status === 'error') {
                                r.innerHTML = '<div class="payment-error">Payment ' + vResult.status + ': ' + vResult.message + '</div>';
                                return;
                            }
                        }
                    }

                    if (confirmed) {
                        // Generate invoice after payment
                        const invResp = await fetch('/api/invoice', {
                            method: 'POST', headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify(data)
                        });
                        const inv = await invResp.json();
                        r.innerHTML = `
                            <h3>Invoice Generated</h3>
                            <div class="result-row"><span>Invoice #</span><span>${inv.invoice_number}</span></div>
                            <div class="result-row"><span>Date</span><span>${inv.date}</span></div>
                            <div class="result-row"><span>Subtotal</span><span>${fmt(inv.subtotal)}</span></div>
                            <div class="result-row"><span>VAT (16%)</span><span>${fmt(inv.vat)}</span></div>
                            <div class="result-row"><span>Grand Total</span><span>${fmt(inv.total)}</span></div>
                            <div class="payment-status">KES 50 paid via M-Pesa</div>
                            <div class="btn-row">
                                <button class="download-btn" onclick="downloadInvoice('${inv.invoice_number}', \`${inv.download_text.replace(/`/g, '\\`')}\`)">Download</button>
                                <button class="print-btn" onclick="window.open('/print/${inv.invoice_number}')">Print</button>
                            </div>
                        `;
                    } else {
                        r.innerHTML = '<div class="payment-notice">Payment not yet confirmed. Try verifying later.</div>';
                    }
                } else {
                    r.innerHTML = '<div class="payment-error">Payment failed: ' + payResult.message + '</div>';
                }
            } catch(err) {
                r.innerHTML = '<div class="payment-error">Error: ' + err.message + '</div>';
            }
        });

        // PAYE Calculator
        document.getElementById('payeForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const salary = parseFloat(new FormData(e.target).get('salary'));
            const resp = await fetch('/api/paye', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({salary})
            });
            const r = await resp.json();
            const el = document.getElementById('payeResult');
            el.innerHTML = `
                <h3>PAYE Breakdown</h3>
                <div class="result-row"><span>Gross Salary</span><span>${fmt(r.gross_salary)}</span></div>
                <div class="result-row"><span>NSSF (6%)</span><span>${fmt(r.nssf)}</span></div>
                <div class="result-row"><span>Taxable Income</span><span>${fmt(r.taxable_income)}</span></div>
                <div class="result-row"><span>Tax Before Relief</span><span>${fmt(r.tax_before_relief)}</span></div>
                <div class="result-row"><span>Personal Relief</span><span>${fmt(r.personal_relief)}</span></div>
                <div class="result-row"><span>PAYE (Tax)</span><span>${fmt(r.tax_after_relief)}</span></div>
                <div class="result-row"><span>NHIF</span><span>${fmt(r.nhif)}</span></div>
                <div class="result-row"><span>NET SALARY</span><span>${fmt(r.net_salary)}</span></div>
                <div class="itax-link">
                    <a href="/tax-returns">File PAYE Return on iTax &rarr;</a>
                </div>
            `;
            el.classList.remove('hidden');
        });

        // VAT Calculator
        document.getElementById('vatForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const fd = new FormData(e.target);
            const data = {
                sales: parseFloat(fd.get('sales')),
                exempt: parseFloat(fd.get('exempt') || 0),
                input_vat: parseFloat(fd.get('input_vat') || 0)
            };
            const resp = await fetch('/api/vat', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const r = await resp.json();
            const el = document.getElementById('vatResult');
            el.innerHTML = `
                <h3>VAT Breakdown</h3>
                <div class="result-row"><span>Output Sales</span><span>${fmt(r.gross_sales)}</span></div>
                <div class="result-row"><span>Exempt Sales</span><span>${fmt(r.vat_exempt)}</span></div>
                <div class="result-row"><span>VAT Collected (16%)</span><span>${fmt(r.vat_collected)}</span></div>
                <div class="result-row"><span>Input VAT</span><span>${fmt(r.input_vat)}</span></div>
                <div class="result-row"><span>NET VAT PAYABLE</span><span>${fmt(r.net_vat_payable)}</span></div>
                <div class="itax-link">
                    <a href="/tax-returns">File VAT Return on iTax &rarr;</a>
                </div>
            `;
            el.classList.remove('hidden');
        });

        // M-Pesa Direct Payment
        document.getElementById('mpesaForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const fd = new FormData(e.target);
            const phone = fd.get('phone');
            const amount = parseFloat(fd.get('amount'));
            const account_ref = fd.get('account_ref') || 'KenyaComply';
            const el = document.getElementById('mpesaResult');
            el.innerHTML = '<div class="payment-notice">Sending STK Push to ' + phone + '...</div>';
            el.classList.remove('hidden');

            try {
                const resp = await fetch('/api/payment/initiate', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({phone, amount, account_ref})
                });
                const r = await resp.json();

                if (r.status === 'success') {
                    const txRef = r.data.tx_ref;
                    el.innerHTML = `
                        <div class="payment-status">STK Push sent! Check your phone.</div>
                        <div class="result-row"><span>Transaction Ref</span><span>${txRef}</span></div>
                        <div class="result-row"><span>Amount</span><span>${fmt(amount)}</span></div>
                        <div class="result-row"><span>Phone</span><span>${r.data.phone}</span></div>
                        ${r.data.demo ? '<div class="payment-notice">DEMO MODE - No real charge</div>' : ''}
                        <div class="btn-row">
                            <button class="download-btn" onclick="checkPayment('${txRef}')">Check Payment Status</button>
                        </div>
                    `;
                } else {
                    el.innerHTML = '<div class="payment-error">Failed: ' + r.message + '</div>';
                }
            } catch(err) {
                el.innerHTML = '<div class="payment-error">Error: ' + err.message + '</div>';
            }
        });

        async function checkPayment(txRef) {
            const resp = await fetch('/api/payment/verify/' + txRef);
            const r = await resp.json();
            const el = document.getElementById('mpesaResult');
            if (r.status === 'success') {
                el.innerHTML = '<div class="payment-status">Payment Confirmed! Receipt: ' + (r.data.mpesa_receipt || 'N/A') + '</div>';
            } else if (r.status === 'pending') {
                el.innerHTML += '<div class="payment-notice">Still pending... Try again in a few seconds.</div>';
            } else {
                el.innerHTML += '<div class="payment-error">' + r.status + ': ' + r.message + '</div>';
            }
        }
    </script>
</body>
</html>
"""

# ============================================
# TAX RETURNS PAGE
# ============================================

TAX_RETURNS_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Tax Returns - KenyaComply</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }
        .container { max-width: 860px; margin: 0 auto; padding: 20px; }
        header { background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%); color: white; padding: 35px 20px; text-align: center; border-radius: 12px; margin-bottom: 25px; }
        h1 { font-size: 2rem; margin-bottom: 8px; }
        .nav { display: flex; gap: 10px; margin-top: 15px; justify-content: center; flex-wrap: wrap; }
        .nav a { color: white; text-decoration: none; padding: 8px 18px; border-radius: 20px; background: rgba(255,255,255,0.15); }
        .nav a:hover { background: rgba(255,255,255,0.25); }
        .tabs { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
        .tab { padding: 12px 20px; background: white; border: none; border-radius: 8px; cursor: pointer; font-size: 0.95rem; box-shadow: 0 2px 5px rgba(0,0,0,0.08); }
        .tab.active { background: #2e7d32; color: white; }
        .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); margin-bottom: 20px; }
        h2 { color: #2e7d32; margin-bottom: 15px; }
        .form-group { margin-bottom: 18px; }
        label { display: block; margin-bottom: 6px; font-weight: 600; font-size: 0.95rem; }
        input, select { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 1rem; box-sizing: border-box; }
        input:focus, select:focus { outline: none; border-color: #2e7d32; }
        .row { display: flex; gap: 15px; flex-wrap: wrap; }
        .col { flex: 1; min-width: 200px; }
        button.primary { background: #2e7d32; color: white; padding: 15px; border: none; border-radius: 8px; font-size: 1.05rem; cursor: pointer; width: 100%; font-weight: 600; }
        button.primary:hover { background: #1b5e20; }
        .result { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #2e7d32; }
        .result h3 { margin-bottom: 12px; color: #2e7d32; }
        .result-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e0e0e0; }
        .result-row:last-child { border-bottom: none; }
        .result-row.total { font-weight: bold; font-size: 1.15rem; background: #e8f5e9; padding: 12px; border-radius: 6px; margin-top: 5px; }
        .steps { counter-reset: step; list-style: none; padding: 0; margin-top: 15px; }
        .steps li { counter-increment: step; padding: 10px 0 10px 40px; position: relative; border-bottom: 1px solid #f0f0f0; }
        .steps li::before { content: counter(step); position: absolute; left: 0; background: #2e7d32; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: bold; }
        .itax-btn { display: inline-block; background: #1565c0; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-top: 15px; font-size: 1rem; }
        .itax-btn:hover { background: #0d47a1; }
        .mpesa-btn { display: inline-block; background: #4CAF50; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-top: 10px; font-size: 1rem; border: none; cursor: pointer; }
        .info-box { background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #1565c0; }
        .info-box h4 { color: #1565c0; margin-bottom: 5px; }
        .warning { background: #fff3cd; padding: 12px; border-radius: 8px; color: #856404; margin: 10px 0; font-weight: 600; text-align: center; }
        .emp-row { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #e0e0e0; }
        .mpesa-btn { background: #4CAF50; }
        .mpesa-btn:hover { background: #388E3C; }
        .payment-notice { background: #fff3cd; color: #856404; padding: 12px; border-radius: 8px; margin: 10px 0; font-weight: 600; text-align: center; }
        .payment-status { background: #d4edda; color: #155724; padding: 12px; border-radius: 8px; margin: 10px 0; text-align: center; font-weight: 600; }
        .payment-error { background: #f8d7da; color: #721c24; padding: 12px; border-radius: 8px; margin: 10px 0; text-align: center; font-weight: 600; }
        .hidden { display: none; }
        footer { text-align: center; padding: 20px; opacity: 0.6; font-size: 0.9rem; }
        @media (max-width: 600px) { .container { padding: 10px; } .card { padding: 20px; } h1 { font-size: 1.6rem; } }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>File Tax Returns</h1>
            <p>Prepare your KRA tax return data, then file on iTax (KES 100 filing fee)</p>
            <div class="nav">
                <a href="/">Home</a>
                <a href="/dashboard">Dashboard</a>
                <a href="/itax-guide">iTax Guide</a>
            </div>
        </header>

        <div class="tabs">
            <button class="tab active" onclick="showReturnTab('income')">Income Tax (IT1)</button>
            <button class="tab" onclick="showReturnTab('payeReturn')">PAYE Return (P10)</button>
            <button class="tab" onclick="showReturnTab('vatReturn')">VAT Return</button>
        </div>

        <!-- Income Tax Return -->
        <div id="income" class="card">
            <h2>Individual Income Tax Return (IT1)</h2>
            <div class="info-box">
                <h4>Deadline: 30th June annually</h4>
                <p>File your annual income tax return. This tool calculates your tax and provides data to enter on iTax.</p>
            </div>
            <form id="incomeForm">
                <div class="form-group">
                    <label>Tax Year</label>
                    <select name="tax_year">
                        <option value="2025">2025</option>
                        <option value="2024" selected>2024</option>
                        <option value="2023">2023</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Annual Employment Income (KES)</label>
                    <input type="number" name="annual_income" placeholder="1200000" required min="0">
                </div>
                <div class="row">
                    <div class="col form-group">
                        <label>Other Income (Rental, Business, etc.)</label>
                        <input type="number" name="other_income" placeholder="0" value="0">
                    </div>
                    <div class="col form-group">
                        <label>Allowable Deductions</label>
                        <input type="number" name="deductions" placeholder="0" value="0">
                    </div>
                </div>
                <div class="row">
                    <div class="col form-group">
                        <label>PAYE Already Paid (P9 Form)</label>
                        <input type="number" name="paye_already_paid" placeholder="Auto-calculated" value="0">
                    </div>
                    <div class="col form-group">
                        <label>Withholding Tax Paid</label>
                        <input type="number" name="withholding_tax" placeholder="0" value="0">
                    </div>
                </div>
                <div class="form-group">
                    <label>M-Pesa Phone (for KES 100 filing fee)</label>
                    <input type="tel" name="phone" placeholder="07XX XXX XXX" required>
                </div>
                <button type="submit" class="primary mpesa-btn">Pay KES 100 & Calculate Return</button>
            </form>
            <div id="incomeResult" class="result hidden"></div>
        </div>

        <!-- PAYE Return -->
        <div id="payeReturn" class="card hidden">
            <h2>Employer PAYE Return (P10)</h2>
            <div class="info-box">
                <h4>Deadline: 9th of the following month</h4>
                <p>Monthly PAYE return for employers. Add employees below to calculate total PAYE due.</p>
            </div>
            <form id="payeReturnForm">
                <div class="form-group">
                    <label>Return Period</label>
                    <select name="period" id="payePeriod">
                        <option>January 2025</option><option>February 2025</option><option selected>March 2025</option>
                        <option>April 2025</option><option>May 2025</option><option>June 2025</option>
                        <option>July 2025</option><option>August 2025</option><option>September 2025</option>
                        <option>October 2025</option><option>November 2025</option><option>December 2025</option>
                    </select>
                </div>
                <div id="employeeList">
                    <div class="emp-row">
                        <div class="row">
                            <div class="col form-group"><label>Employee Name</label><input type="text" class="emp-name" placeholder="John Doe"></div>
                            <div class="col form-group"><label>KRA PIN</label><input type="text" class="emp-pin" placeholder="A123456789B"></div>
                            <div class="col form-group"><label>Gross Salary</label><input type="number" class="emp-gross" placeholder="100000"></div>
                        </div>
                    </div>
                </div>
                <button type="button" onclick="addEmployee()" style="background:#e8f5e9; color:#2e7d32; border:2px solid #2e7d32; padding:10px 20px; border-radius:8px; cursor:pointer; font-weight:600; margin-bottom:15px;">+ Add Employee</button>
                <div class="form-group">
                    <label>M-Pesa Phone (for KES 100 filing fee)</label>
                    <input type="tel" name="phone" id="payePhone" placeholder="07XX XXX XXX" required>
                </div>
                <button type="submit" class="primary mpesa-btn">Pay KES 100 & Calculate PAYE Return</button>
            </form>
            <div id="payeReturnResult" class="result hidden"></div>
        </div>

        <!-- VAT Return -->
        <div id="vatReturn" class="card hidden">
            <h2>VAT Return</h2>
            <div class="info-box">
                <h4>Deadline: 20th of the following month</h4>
                <p>Monthly VAT return for VAT-registered businesses (turnover > KES 5M/year).</p>
            </div>
            <form id="vatReturnForm">
                <div class="form-group">
                    <label>Return Period</label>
                    <select name="period" id="vatPeriod">
                        <option>January 2025</option><option>February 2025</option><option selected>March 2025</option>
                        <option>April 2025</option><option>May 2025</option><option>June 2025</option>
                        <option>July 2025</option><option>August 2025</option><option>September 2025</option>
                        <option>October 2025</option><option>November 2025</option><option>December 2025</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Total Output Sales (KES)</label>
                    <input type="number" name="output_sales" placeholder="500000" required min="0">
                </div>
                <div class="row">
                    <div class="col form-group">
                        <label>Exempt Sales (KES)</label>
                        <input type="number" name="exempt_sales" placeholder="0" value="0">
                    </div>
                    <div class="col form-group">
                        <label>Input VAT (KES)</label>
                        <input type="number" name="input_vat" placeholder="0" value="0">
                    </div>
                </div>
                <div class="form-group">
                    <label>M-Pesa Phone (for KES 100 filing fee)</label>
                    <input type="tel" name="phone" id="vatPhone" placeholder="07XX XXX XXX" required>
                </div>
                <button type="submit" class="primary mpesa-btn">Pay KES 100 & Calculate VAT Return</button>
            </form>
            <div id="vatReturnResult" class="result hidden"></div>
        </div>

        <footer>KenyaComply v2.0 | <a href="/itax-guide" style="color:#666;">iTax Filing Guide</a></footer>
    </div>

    <script>
        function showReturnTab(tabId) {
            document.querySelectorAll('.card').forEach(c => c.classList.add('hidden'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById(tabId).classList.remove('hidden');
            event.target.classList.add('active');
        }

        function fmt(n) { return 'KES ' + Math.round(n).toLocaleString(); }

        function addEmployee() {
            const list = document.getElementById('employeeList');
            const row = document.createElement('div');
            row.className = 'emp-row';
            row.innerHTML = `<div class="row">
                <div class="col form-group"><label>Employee Name</label><input type="text" class="emp-name" placeholder="Jane Doe"></div>
                <div class="col form-group"><label>KRA PIN</label><input type="text" class="emp-pin" placeholder="A123456789B"></div>
                <div class="col form-group"><label>Gross Salary</label><input type="number" class="emp-gross" placeholder="80000"></div>
            </div>`;
            list.appendChild(row);
        }

        // M-Pesa payment helper for tax returns (KES 100)
        async function payAndProcess(phone, resultEl, processCallback) {
            resultEl.innerHTML = '<div class="payment-notice">Sending M-Pesa STK Push for KES 100 filing fee...</div>';
            resultEl.classList.remove('hidden');
            try {
                const payResp = await fetch('/api/payment/initiate', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({phone, amount: 100, account_ref: 'KenyaComply Tax Return'})
                });
                const payResult = await payResp.json();
                if (payResult.status !== 'success') {
                    resultEl.innerHTML = '<div class="payment-error">Payment failed: ' + payResult.message + '</div>';
                    return;
                }
                const txRef = payResult.data.tx_ref;
                resultEl.innerHTML = '<div class="payment-status">STK Push sent! Check your phone for M-Pesa prompt.</div>';
                let confirmed = payResult.data.demo;
                if (!confirmed) {
                    resultEl.innerHTML += '<div class="payment-notice">Waiting for payment confirmation...</div>';
                    for (let i = 0; i < 6; i++) {
                        await new Promise(resolve => setTimeout(resolve, 5000));
                        const vResp = await fetch('/api/payment/verify/' + txRef);
                        const vResult = await vResp.json();
                        if (vResult.status === 'success') { confirmed = true; break; }
                        if (vResult.status === 'cancelled' || vResult.status === 'error') {
                            resultEl.innerHTML = '<div class="payment-error">Payment ' + vResult.status + ': ' + vResult.message + '</div>';
                            return;
                        }
                    }
                }
                if (!confirmed) {
                    resultEl.innerHTML = '<div class="payment-notice">Payment not yet confirmed. Please try again.</div>';
                    return;
                }
                resultEl.innerHTML = '<div class="payment-status">KES 100 filing fee paid via M-Pesa</div>';
                await processCallback(resultEl);
            } catch(err) {
                resultEl.innerHTML = '<div class="payment-error">Error: ' + err.message + '</div>';
            }
        }

        // Income Tax Return
        document.getElementById('incomeForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const fd = new FormData(e.target);
            const phone = fd.get('phone');
            if (!phone || phone.replace(/\\s/g,'').length < 10) { alert('Enter a valid M-Pesa phone number'); return; }
            const el = document.getElementById('incomeResult');
            const data = {
                return_type: 'income_tax',
                tax_year: fd.get('tax_year'),
                annual_income: parseFloat(fd.get('annual_income') || 0),
                other_income: parseFloat(fd.get('other_income') || 0),
                deductions: parseFloat(fd.get('deductions') || 0),
                paye_already_paid: parseFloat(fd.get('paye_already_paid') || 0),
                withholding_tax: parseFloat(fd.get('withholding_tax') || 0)
            };
            await payAndProcess(phone, el, async (resultEl) => {
                const resp = await fetch('/api/tax-return', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const r = await resp.json();
                const balanceClass = r.tax_balance < 0 ? 'color:#2e7d32' : 'color:#d32f2f';
                resultEl.innerHTML += `
                    <h3>Income Tax Return - ${r.tax_year}</h3>
                    <div class="result-row"><span>Ref</span><span>${r.ref}</span></div>
                    <div class="result-row"><span>Employment Income</span><span>${fmt(r.employment_income)}</span></div>
                    <div class="result-row"><span>Other Income</span><span>${fmt(r.other_income)}</span></div>
                    <div class="result-row"><span>Total Income</span><span>${fmt(r.total_income)}</span></div>
                    <div class="result-row"><span>NSSF Deduction</span><span>${fmt(r.nssf_deduction)}</span></div>
                    <div class="result-row"><span>Other Deductions</span><span>${fmt(r.other_deductions)}</span></div>
                    <div class="result-row"><span>Taxable Income</span><span>${fmt(r.taxable_income)}</span></div>
                    <div class="result-row"><span>Tax Charged</span><span>${fmt(r.tax_charged)}</span></div>
                    <div class="result-row"><span>Personal Relief</span><span>${fmt(r.personal_relief)}</span></div>
                    <div class="result-row"><span>PAYE Already Paid</span><span>${fmt(r.paye_already_paid)}</span></div>
                    <div class="result-row"><span>Withholding Tax</span><span>${fmt(r.withholding_tax)}</span></div>
                    <div class="result-row total"><span>${r.refund_or_payable}</span><span style="${balanceClass}">${fmt(Math.abs(r.tax_balance))}</span></div>
                    <h4 style="margin-top:20px; color:#1565c0;">Steps to File on iTax:</h4>
                    <ol class="steps">${r.filing_steps.map(s => '<li>' + s + '</li>').join('')}</ol>
                    <a href="https://itax.kra.go.ke" target="_blank" class="itax-btn">Open iTax Portal</a>
                `;
            });
        });

        // PAYE Return
        document.getElementById('payeReturnForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const phone = document.getElementById('payePhone').value;
            if (!phone || phone.replace(/\\s/g,'').length < 10) { alert('Enter a valid M-Pesa phone number'); return; }
            const employees = [];
            document.querySelectorAll('.emp-row').forEach(row => {
                const name = row.querySelector('.emp-name').value;
                const pin = row.querySelector('.emp-pin').value;
                const gross = row.querySelector('.emp-gross').value;
                if (gross) employees.push({name, pin, gross: parseFloat(gross)});
            });
            if (!employees.length) { alert('Add at least one employee'); return; }
            const period = document.getElementById('payePeriod').value;
            const el = document.getElementById('payeReturnResult');
            await payAndProcess(phone, el, async (resultEl) => {
                const resp = await fetch('/api/tax-return', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({return_type: 'paye', period, employees})
                });
                const r = await resp.json();
                let empRows = r.employees.map(e =>
                    `<div class="emp-row"><div class="row">
                        <div class="col"><strong>${e.name || 'Employee'}</strong> (${e.pin || 'N/A'})</div>
                        <div class="col">Gross: ${fmt(e.gross)}</div>
                        <div class="col">PAYE: ${fmt(e.paye)}</div>
                        <div class="col">Net: ${fmt(e.net)}</div>
                    </div></div>`
                ).join('');
                resultEl.innerHTML += `
                    <h3>PAYE Return (P10) - ${r.period}</h3>
                    <div class="result-row"><span>Ref</span><span>${r.ref}</span></div>
                    <div class="result-row"><span>Employees</span><span>${r.total_employees}</span></div>
                    ${empRows}
                    <div class="result-row total"><span>Total PAYE Due</span><span>${fmt(r.total_paye)}</span></div>
                    <h4 style="margin-top:20px; color:#1565c0;">Steps to File:</h4>
                    <ol class="steps">${r.filing_steps.map(s => '<li>' + s + '</li>').join('')}</ol>
                    <a href="https://itax.kra.go.ke" target="_blank" class="itax-btn">Open iTax Portal</a>
                `;
            });
        });

        // VAT Return
        document.getElementById('vatReturnForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const phone = document.getElementById('vatPhone').value;
            if (!phone || phone.replace(/\\s/g,'').length < 10) { alert('Enter a valid M-Pesa phone number'); return; }
            const fd = new FormData(e.target);
            const data = {
                return_type: 'vat',
                period: document.getElementById('vatPeriod').value,
                output_sales: parseFloat(fd.get('output_sales') || 0),
                exempt_sales: parseFloat(fd.get('exempt_sales') || 0),
                input_vat: parseFloat(fd.get('input_vat') || 0)
            };
            const el = document.getElementById('vatReturnResult');
            await payAndProcess(phone, el, async (resultEl) => {
                const resp = await fetch('/api/tax-return', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const r = await resp.json();
                resultEl.innerHTML += `
                    <h3>VAT Return - ${r.period}</h3>
                    <div class="result-row"><span>Ref</span><span>${r.ref}</span></div>
                    <div class="result-row"><span>Output Sales</span><span>${fmt(r.output_sales)}</span></div>
                    <div class="result-row"><span>Exempt Sales</span><span>${fmt(r.exempt_sales)}</span></div>
                    <div class="result-row"><span>VAT Collected (16%)</span><span>${fmt(r.vat_collected)}</span></div>
                    <div class="result-row"><span>Input VAT</span><span>${fmt(r.input_vat)}</span></div>
                    <div class="result-row total"><span>Net VAT Payable</span><span>${fmt(r.net_vat_payable)}</span></div>
                    <h4 style="margin-top:20px; color:#1565c0;">Steps to File:</h4>
                    <ol class="steps">${r.filing_steps.map(s => '<li>' + s + '</li>').join('')}</ol>
                    <a href="https://itax.kra.go.ke" target="_blank" class="itax-btn">Open iTax Portal</a>
                `;
            });
        });
    </script>
</body>
</html>
"""

# ============================================
# iTAX GUIDE PAGE
# ============================================

ITAX_GUIDE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>iTax Filing Guide - KenyaComply</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; line-height: 1.7; }
        .container { max-width: 860px; margin: 0 auto; padding: 20px; }
        header { background: linear-gradient(135deg, #1565c0 0%, #0d47a1 100%); color: white; padding: 35px 20px; text-align: center; border-radius: 12px; margin-bottom: 25px; }
        h1 { font-size: 2rem; margin-bottom: 8px; }
        .nav { display: flex; gap: 10px; margin-top: 15px; justify-content: center; flex-wrap: wrap; }
        .nav a { color: white; text-decoration: none; padding: 8px 18px; border-radius: 20px; background: rgba(255,255,255,0.15); }
        .card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 20px; }
        h2 { color: #1565c0; margin-bottom: 15px; font-size: 1.4rem; }
        h3 { color: #1a1a2e; margin: 20px 0 10px; }
        .steps { counter-reset: step; list-style: none; padding: 0; }
        .steps li { counter-increment: step; padding: 12px 0 12px 45px; position: relative; border-bottom: 1px solid #f0f0f0; }
        .steps li::before { content: counter(step); position: absolute; left: 0; top: 10px; background: #1565c0; color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.9rem; font-weight: bold; }
        .steps li:last-child { border-bottom: none; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { border: 1px solid #e0e0e0; padding: 12px; text-align: left; }
        th { background: #e3f2fd; color: #1565c0; }
        .deadline { color: #d32f2f; font-weight: bold; }
        .highlight { background: #e8f5e9; padding: 15px; border-radius: 8px; border-left: 4px solid #2e7d32; margin: 15px 0; }
        .warning { background: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #f9a825; margin: 15px 0; }
        .itax-btn { display: inline-block; background: #1565c0; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; margin: 8px 5px; }
        .itax-btn.green { background: #2e7d32; }
        .itax-btn:hover { opacity: 0.9; }
        .contact { background: #f8f9fa; padding: 20px; border-radius: 8px; }
        .contact p { margin: 5px 0; }
        footer { text-align: center; padding: 20px; opacity: 0.6; font-size: 0.9rem; }
        @media (max-width: 600px) { .container { padding: 10px; } .card { padding: 18px; } }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>KRA iTax Filing Guide</h1>
            <p>Step-by-step guide to filing your taxes on the KRA iTax portal</p>
            <div class="nav">
                <a href="/">Home</a>
                <a href="/dashboard">Dashboard</a>
                <a href="/tax-returns">File Returns</a>
            </div>
        </header>

        <div class="card">
            <h2>Tax Filing Deadlines</h2>
            <table>
                <tr><th>Tax Type</th><th>Who Must File</th><th>Deadline</th><th>Penalty</th></tr>
                <tr><td>Income Tax (IT1)</td><td>All individuals with income</td><td class="deadline">30th June</td><td>KES 20,000 or 5% of tax due</td></tr>
                <tr><td>PAYE (P10)</td><td>Employers</td><td class="deadline">9th of next month</td><td>25% of PAYE due + 5%/month interest</td></tr>
                <tr><td>VAT</td><td>Businesses (turnover > KES 5M)</td><td class="deadline">20th of next month</td><td>KES 10,000 + 5% of VAT due</td></tr>
                <tr><td>Corporate Tax</td><td>Companies</td><td class="deadline">6th month after year-end</td><td>5% of tax due + 1%/month</td></tr>
                <tr><td>Turnover Tax (TOT)</td><td>Small businesses (< KES 25M)</td><td class="deadline">20th of next month</td><td>KES 1,000/month late</td></tr>
            </table>
        </div>

        <div class="card">
            <h2>How to File Income Tax Return (IT1)</h2>
            <div class="warning">
                <strong>You need:</strong> KRA PIN, P9 form from employer, bank interest certificates, rental income records
            </div>
            <ol class="steps">
                <li>Go to <strong>itax.kra.go.ke</strong> and log in with your KRA PIN and password</li>
                <li>Click <strong>Returns</strong> from the top menu, then <strong>File Return</strong></li>
                <li>Select <strong>Income Tax - Resident Individual</strong> and the correct tax year</li>
                <li>Fill in <strong>Section A</strong>: Employment income from your P9 form (basic salary, allowances, benefits)</li>
                <li>Fill in <strong>Section B</strong>: Other income (rental income, business income, interest, dividends)</li>
                <li>Fill in <strong>Section C</strong>: Deductions (NSSF, life insurance, mortgage interest, pension contributions)</li>
                <li>Review the auto-calculated tax. The system deducts personal relief (KES 28,800/year) automatically</li>
                <li>Enter PAYE already deducted (from P9) and any withholding tax credits</li>
                <li>Submit the return. If tax is due, pay via M-Pesa (Paybill 572572) or bank</li>
                <li>Download and save the acknowledgement receipt</li>
            </ol>
            <div class="highlight">
                <strong>Tip:</strong> Use KenyaComply's <a href="/tax-returns">Tax Return Calculator</a> to prepare your figures before logging into iTax. This saves time and reduces errors.
            </div>
            <a href="https://itax.kra.go.ke" target="_blank" class="itax-btn">Open iTax Portal</a>
            <a href="/tax-returns" class="itax-btn green">Calculate Your Tax First</a>
        </div>

        <div class="card">
            <h2>How to File PAYE Return (P10) - Employers</h2>
            <ol class="steps">
                <li>Log in to iTax with your company's KRA PIN</li>
                <li>Go to <strong>Returns > File Return > PAYE</strong></li>
                <li>Select the return period (month/year)</li>
                <li>Choose <strong>Upload CSV</strong> or <strong>Fill Online</strong></li>
                <li>For each employee: enter KRA PIN, gross pay, taxable pay, PAYE deducted, NSSF, NHIF</li>
                <li>System auto-totals. Verify total PAYE matches your payroll</li>
                <li>Submit and pay total PAYE via M-Pesa Paybill <strong>572572</strong></li>
                <li>Issue P9 forms to employees by end of February for annual filing</li>
            </ol>
            <div class="highlight">
                Use KenyaComply's <a href="/tax-returns">PAYE Return Calculator</a> to compute each employee's PAYE before filing.
            </div>
        </div>

        <div class="card">
            <h2>How to File VAT Return</h2>
            <ol class="steps">
                <li>Log in to iTax with your company's KRA PIN</li>
                <li>Go to <strong>Returns > File Return > VAT</strong></li>
                <li>Select the return period</li>
                <li>Enter <strong>Output VAT</strong> (16% of taxable sales you made)</li>
                <li>Enter <strong>Input VAT</strong> (VAT you paid on purchases with valid tax invoices)</li>
                <li>System calculates net VAT payable (Output - Input)</li>
                <li>Submit and pay via M-Pesa Paybill <strong>572572</strong> or bank</li>
            </ol>
            <div class="warning">
                <strong>Important:</strong> Keep all ETIMS invoices for 5 years. KRA can audit anytime.
                Use KenyaComply to generate ETIMS-compliant invoices.
            </div>
        </div>

        <div class="card">
            <h2>M-Pesa Tax Payment</h2>
            <div class="highlight">
                <h3>Pay KRA via M-Pesa</h3>
                <ol class="steps">
                    <li>Go to M-Pesa > <strong>Lipa na M-Pesa > Pay Bill</strong></li>
                    <li>Business Number: <strong>572572</strong></li>
                    <li>Account Number: Your <strong>KRA PIN + Tax Type</strong> (e.g., A123456789B + IT for Income Tax)</li>
                    <li>Enter amount and your M-Pesa PIN</li>
                    <li>You'll receive a confirmation SMS. Save it!</li>
                </ol>
            </div>
            <table>
                <tr><th>Tax Type</th><th>Account Format</th><th>Example</th></tr>
                <tr><td>Income Tax</td><td>PIN + IT</td><td>A123456789BIT</td></tr>
                <tr><td>PAYE</td><td>PIN + PAYE</td><td>A123456789BPAYE</td></tr>
                <tr><td>VAT</td><td>PIN + VAT</td><td>A123456789BVAT</td></tr>
                <tr><td>Corporate Tax</td><td>PIN + CT</td><td>P123456789ACT</td></tr>
            </table>
        </div>

        <div class="card">
            <h2>Nil Returns</h2>
            <p>Even if you had <strong>no income</strong>, you must still file a nil return to avoid penalties.</p>
            <ol class="steps">
                <li>Log in to iTax</li>
                <li>Go to Returns > File Return > Income Tax Resident Individual</li>
                <li>Select "Nil Return" option</li>
                <li>Submit - no payment needed</li>
            </ol>
        </div>

        <div class="card contact">
            <h2>KRA Help Contacts</h2>
            <p><strong>Phone:</strong> 020-4-999-999 / 0711-099-999</p>
            <p><strong>Email:</strong> callcentre@kra.go.ke</p>
            <p><strong>WhatsApp:</strong> 0728-606-161</p>
            <p><strong>Nearest KRA Office:</strong> <a href="https://www.kra.go.ke/helping-tax-payers/stations" target="_blank">Find your local office</a></p>
            <p><strong>iTax Help:</strong> <a href="https://itax.kra.go.ke" target="_blank">itax.kra.go.ke</a></p>
        </div>

        <footer>KenyaComply v2.0 | <a href="/" style="color:#666;">Back to Home</a></footer>
    </div>
</body>
</html>
"""

# Run the app
app.debug = True
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
