# KenyaComply v3.1 - Full Tax Compliance Platform + AI Tax Agent
# ETIMS Invoices | M-Pesa Payments | Tax Returns | Payroll | Expense Tracking | P&L | AI Agent

from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import json
import os
import uuid
import hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kenyacomply-dev-secret-key-v3')

from etims_invoice import create_standard_invoice, ETIMSInvoice, Party, InvoiceItem
from tax_calculator import (
    calculate_paye, calculate_vat, calculate_nhif,
    calculate_corporate_tax, calculate_turnover_tax,
    calculate_withholding_tax, WITHHOLDING_RATES
)
from mpesa import (
    initiate_mpesa_payment, verify_mpesa_payment,
    process_mpesa_callback, PAYMENT_CONFIG
)
from payroll import process_payroll, generate_p9_form, generate_p9_text, generate_payslip_text
from tax_agent import (
    analyze_user_data, auto_prepare_return, generate_filing_csv,
    get_upcoming_deadlines, ask_tax_advisor
)
from database import (
    create_user, get_user_by_email, get_user_by_id, update_user,
    create_business, get_businesses,
    save_invoice, get_invoices, get_invoice,
    save_payment, get_payments, update_payment,
    save_tax_return, get_tax_returns,
    save_expense, save_expenses_bulk, get_expenses, get_expense_summary,
    save_employee, get_employees, update_employee, delete_employee,
    save_payroll_run, get_payroll_runs,
    get_profit_loss, DEMO_MODE as DB_DEMO_MODE
)

# ============================================
# PRICING
# ============================================
PRICES = {
    'invoice': 50,
    'tax_return': 100,
    'payroll': 150,
    'p9_form': 100,
}

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def get_current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return get_user_by_id(uid)

# ============================================
# SHARED CSS
# ============================================
BASE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }
.container { max-width: 900px; margin: 0 auto; padding: 20px; }
.navbar { background: #1a1a2e; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
.navbar .logo { font-size: 1.4rem; font-weight: bold; text-decoration: none; color: white; }
.navbar nav { display: flex; gap: 8px; flex-wrap: wrap; }
.navbar nav a { color: rgba(255,255,255,0.85); text-decoration: none; padding: 6px 14px; border-radius: 6px; font-size: 0.9rem; }
.navbar nav a:hover, .navbar nav a.active { background: rgba(255,255,255,0.15); color: white; }
.card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 20px; }
h1 { color: #1a1a2e; margin-bottom: 8px; }
h2 { color: #1a1a2e; margin-bottom: 15px; }
.form-group { margin-bottom: 16px; }
label { display: block; margin-bottom: 5px; font-weight: 600; font-size: 0.93rem; }
input, select, textarea { width: 100%; padding: 11px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 1rem; box-sizing: border-box; }
input:focus, select:focus, textarea:focus { outline: none; border-color: #1a1a2e; }
.row { display: flex; gap: 15px; flex-wrap: wrap; }
.col { flex: 1; min-width: 200px; }
.btn { display: inline-block; padding: 12px 22px; border-radius: 8px; font-weight: 600; font-size: 0.95rem; text-decoration: none; border: none; cursor: pointer; text-align: center; }
.btn-primary { background: #1a1a2e; color: white; }
.btn-primary:hover { background: #16213e; }
.btn-green { background: #2e7d32; color: white; }
.btn-green:hover { background: #1b5e20; }
.btn-blue { background: #1565c0; color: white; }
.btn-blue:hover { background: #0d47a1; }
.btn-mpesa { background: #4CAF50; color: white; }
.btn-mpesa:hover { background: #388E3C; }
.btn-outline { background: transparent; border: 2px solid #1a1a2e; color: #1a1a2e; }
.btn-sm { padding: 8px 16px; font-size: 0.85rem; }
.btn-full { width: 100%; }
.btn-danger { background: #d32f2f; color: white; }
.result { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 15px; border-left: 4px solid #1a1a2e; }
.result h3 { margin-bottom: 10px; color: #1a1a2e; }
.result-row { display: flex; justify-content: space-between; padding: 9px 0; border-bottom: 1px solid #e0e0e0; }
.result-row:last-child { border-bottom: none; }
.result-row.total { font-weight: bold; font-size: 1.1rem; background: #e8f5e9; padding: 10px; border-radius: 6px; margin-top: 5px; }
.tabs { display: flex; gap: 6px; margin-bottom: 20px; flex-wrap: wrap; }
.tab { padding: 10px 18px; background: white; border: none; border-radius: 8px; cursor: pointer; font-size: 0.9rem; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.tab.active { background: #1a1a2e; color: white; }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
.stat { background: #f8f9fa; padding: 18px; border-radius: 8px; text-align: center; }
.stat-value { font-size: 1.6rem; font-weight: bold; color: #1a1a2e; }
.stat-label { color: #666; font-size: 0.85rem; }
.alert { padding: 12px 15px; border-radius: 8px; margin-bottom: 15px; font-weight: 600; }
.alert-info { background: #e3f2fd; color: #1565c0; }
.alert-success { background: #d4edda; color: #155724; }
.alert-warning { background: #fff3cd; color: #856404; }
.alert-danger { background: #f8d7da; color: #721c24; }
.badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600; }
.badge-green { background: #e8f5e9; color: #2e7d32; }
.badge-blue { background: #e3f2fd; color: #1565c0; }
.badge-gray { background: #f0f0f0; color: #666; }
.steps { counter-reset: step; list-style: none; padding: 0; }
.steps li { counter-increment: step; padding: 10px 0 10px 40px; position: relative; border-bottom: 1px solid #f0f0f0; }
.steps li::before { content: counter(step); position: absolute; left: 0; top: 8px; background: #1a1a2e; color: white; width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.8rem; font-weight: bold; }
table { width: 100%; border-collapse: collapse; margin: 10px 0; }
th, td { border: 1px solid #e0e0e0; padding: 10px; text-align: left; font-size: 0.93rem; }
th { background: #f8f9fa; font-weight: 600; }
.hidden { display: none; }
footer { text-align: center; padding: 25px; opacity: 0.5; font-size: 0.85rem; }
@media (max-width: 640px) { .container { padding: 10px; } .card { padding: 18px; } .navbar nav a { padding: 5px 10px; font-size: 0.8rem; } }
"""

# Shared JS helpers
BASE_JS = """
function fmt(n) { return 'KES ' + Math.round(n).toLocaleString(); }
function showTab(tabId, evt) {
    document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(tabId).classList.remove('hidden');
    if(evt) evt.target.classList.add('active');
}
function download(filename, text) {
    const blob = new Blob([text], {type:'text/plain'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename; document.body.appendChild(a); a.click(); a.remove();
}
async function mpesaPay(phone, amount, ref, resultEl) {
    resultEl.innerHTML = '<div class="alert alert-warning">Sending M-Pesa STK Push for KES '+amount+'...</div>';
    resultEl.classList.remove('hidden');
    const resp = await fetch('/api/payment/initiate', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({phone, amount, account_ref: ref})
    });
    const r = await resp.json();
    if (r.status !== 'success') {
        resultEl.innerHTML = '<div class="alert alert-danger">Payment failed: '+r.message+'</div>';
        return false;
    }
    const txRef = r.data.tx_ref;
    if (r.data.demo) {
        resultEl.innerHTML = '<div class="alert alert-success">KES '+amount+' paid (Demo Mode)</div>';
        return true;
    }
    resultEl.innerHTML = '<div class="alert alert-success">STK Push sent! Check your phone...</div>';
    for (let i = 0; i < 6; i++) {
        await new Promise(r => setTimeout(r, 5000));
        const v = await fetch('/api/payment/verify/'+txRef);
        const vr = await v.json();
        if (vr.status === 'success') {
            resultEl.innerHTML = '<div class="alert alert-success">KES '+amount+' paid via M-Pesa</div>';
            return true;
        }
        if (vr.status === 'cancelled' || vr.status === 'error') {
            resultEl.innerHTML = '<div class="alert alert-danger">'+vr.message+'</div>';
            return false;
        }
    }
    resultEl.innerHTML = '<div class="alert alert-warning">Payment not confirmed yet. Try again.</div>';
    return false;
}
"""

NAVBAR_HTML = """
<div class="navbar">
    <a href="/" class="logo">KenyaComply</a>
    <nav>
        <a href="/">Home</a>
        <a href="/dashboard">Dashboard</a>
        <a href="/invoices">Invoices</a>
        <a href="/tax-returns">Tax Returns</a>
        <a href="/expenses">Expenses</a>
        <a href="/payroll">Payroll</a>
        <a href="/reports">Reports</a>
        <a href="/itax-guide">iTax Guide</a>
        <a href="/agent">AI Agent</a>
        {% if session.get('user_id') %}
            <a href="/logout">Logout</a>
        {% else %}
            <a href="/login">Login</a>
        {% endif %}
    </nav>
</div>
"""

FOOTER_HTML = '<footer>KenyaComply v3.0 | Built by Mwakulomba</footer>'

# ============================================
# AUTH ROUTES
# ============================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '')
        kra_pin = request.form.get('kra_pin', '').strip().upper()
        phone = request.form.get('phone', '').strip()

        if not email:
            error = 'Email is required'
        else:
            user = get_user_by_email(email)
            if user:
                if password and user.get('password_hash') and user['password_hash'] != hash_password(password):
                    error = 'Invalid password'
                else:
                    if kra_pin and kra_pin != user.get('kra_pin'):
                        update_user(user['id'], {'kra_pin': kra_pin})
                    if phone:
                        update_user(user['id'], {'phone': phone})
                    session['user_id'] = user['id']
                    session['email'] = email
                    return redirect(url_for('dashboard'))
            else:
                user = create_user(email, name, hash_password(password) if password else '', kra_pin, phone)
                session['user_id'] = user['id']
                session['email'] = email
                return redirect(url_for('dashboard'))

    return render_template_string("""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Login - KenyaComply</title>
<style>""" + BASE_CSS + """
.login-wrap { display:flex; align-items:center; justify-content:center; min-height:100vh; background:linear-gradient(135deg,#1a1a2e,#16213e); }
.login-card { background:white; padding:40px; border-radius:16px; box-shadow:0 8px 32px rgba(0,0,0,0.2); width:100%; max-width:440px; }
.login-card h1 { text-align:center; margin-bottom:5px; }
.login-card .sub { text-align:center; color:#666; margin-bottom:25px; }
.hint { font-size:0.82rem; color:#999; margin-top:3px; }
.error { background:#f8d7da; color:#721c24; padding:10px; border-radius:8px; margin-bottom:15px; text-align:center; }
</style></head><body>
<div class="login-wrap"><div class="login-card">
<h1>KenyaComply</h1>
<p class="sub">Tax Compliance Platform</p>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
<form method="POST">
<div class="form-group"><label>Email</label><input type="email" name="email" required placeholder="you@company.co.ke"></div>
<div class="form-group"><label>Your Name</label><input type="text" name="name" placeholder="John Doe"></div>
<div class="form-group"><label>Password</label><input type="password" name="password" placeholder="Create or enter password"></div>
<div class="row">
<div class="col form-group"><label>KRA PIN</label><input type="text" name="kra_pin" placeholder="A123456789B"><div class="hint">Format: A123456789B</div></div>
<div class="col form-group"><label>Phone</label><input type="tel" name="phone" placeholder="0712345678"></div>
</div>
<button class="btn btn-primary btn-full" type="submit">Continue</button>
</form>
<p style="text-align:center; margin-top:15px;"><a href="/" style="color:#666;">Back to home</a></p>
</div></div></body></html>
""", error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ============================================
# HOME PAGE
# ============================================
@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KenyaComply - Tax Compliance & M-Pesa Payments</title>
<style>""" + BASE_CSS + """
.hero { background:linear-gradient(135deg,#1a1a2e,#16213e); color:white; padding:50px 20px; text-align:center; border-radius:12px; margin-bottom:25px; }
.hero h1 { font-size:2.2rem; color:white; }
.hero p { opacity:0.85; margin-top:8px; font-size:1.05rem; }
.hero .badges { margin-top:18px; }
.hero .badge { background:rgba(255,255,255,0.15); color:white; margin:3px; }
.features { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:15px; margin-bottom:25px; }
.feature { background:white; padding:25px; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,0.06); text-align:center; }
.feature h3 { color:#1a1a2e; margin:10px 0 8px; }
.feature p { color:#666; font-size:0.9rem; }
.feature .icon { font-size:2rem; }
</style></head><body>
""" + NAVBAR_HTML + """
<div class="container">
<div class="hero">
    <h1>KenyaComply</h1>
    <p>Complete Tax Compliance, M-Pesa Payments & Business Management</p>
    <div class="badges">
        <span class="badge">ETIMS Invoices</span>
        <span class="badge">M-Pesa STK Push</span>
        <span class="badge">Tax Returns</span>
        <span class="badge">KRA iTax</span>
        <span class="badge">Payroll</span>
        <span class="badge">Expenses</span>
        <span class="badge">P&L Reports</span>
    </div>
    <div style="margin-top:20px;">
        <a href="/login" class="btn btn-green" style="margin:5px;">Get Started</a>
        <a href="/calculators" class="btn btn-outline" style="border-color:white; color:white; margin:5px;">Tax Calculators</a>
    </div>
</div>

<div class="features">
    <div class="feature"><div class="icon">&#x1F4C4;</div><h3>ETIMS Invoices</h3><p>Generate KRA-compliant invoices. Multi-item, credit notes, recurring. Download or print.</p><a href="/invoices" class="btn btn-sm btn-primary" style="margin-top:10px;">Create Invoice</a></div>
    <div class="feature"><div class="icon">&#x1F4B3;</div><h3>M-Pesa Payments</h3><p>Safaricom STK Push. Pay for services, collect from clients. Real-time confirmation.</p><a href="/pay" class="btn btn-sm btn-mpesa" style="margin-top:10px;">Pay Now</a></div>
    <div class="feature"><div class="icon">&#x1F4CA;</div><h3>Tax Returns</h3><p>Income Tax, PAYE (P10), VAT, Corporate Tax, Turnover Tax. Step-by-step iTax filing.</p><a href="/tax-returns" class="btn btn-sm btn-green" style="margin-top:10px;">File Returns</a></div>
    <div class="feature"><div class="icon">&#x1F4B0;</div><h3>Tax Calculators</h3><p>PAYE, VAT, Corporate Tax, Turnover Tax, Withholding Tax. Instant results.</p><a href="/calculators" class="btn btn-sm btn-blue" style="margin-top:10px;">Calculate</a></div>
    <div class="feature"><div class="icon">&#x1F465;</div><h3>Payroll</h3><p>Monthly salary processing. Auto PAYE/NSSF/NHIF. Payslips. P9 forms for employees.</p><a href="/payroll" class="btn btn-sm btn-primary" style="margin-top:10px;">Run Payroll</a></div>
    <div class="feature"><div class="icon">&#x1F4DD;</div><h3>Expense Tracker</h3><p>Log purchases with input VAT. Categories. Supplier records. VAT offset tracking.</p><a href="/expenses" class="btn btn-sm btn-primary" style="margin-top:10px;">Track Expenses</a></div>
    <div class="feature"><div class="icon">&#x1F4C8;</div><h3>P&L Reports</h3><p>Revenue vs expenses. Profit margins. VAT summary. Export for accountant.</p><a href="/reports" class="btn btn-sm btn-blue" style="margin-top:10px;">View Reports</a></div>
    <div class="feature"><div class="icon">&#x1F4CB;</div><h3>iTax Guide</h3><p>Step-by-step filing for every tax type. Deadlines. Penalties. KRA contacts.</p><a href="/itax-guide" class="btn btn-sm btn-primary" style="margin-top:10px;">Read Guide</a></div>
    <div class="feature"><div class="icon">&#x1F916;</div><h3>AI Tax Agent</h3><p>Auto-analyzes your data, calculates obligations, prepares returns, and answers tax questions.</p><a href="/agent" class="btn btn-sm btn-green" style="margin-top:10px;">Launch Agent</a></div>
</div>
</div>
""" + FOOTER_HTML + "</body></html>")

# ============================================
# DASHBOARD
# ============================================
@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect('/login')
    invoices = get_invoices(user['id'], limit=10)
    payments = get_payments(user['id'], limit=10)
    returns = get_tax_returns(user['id'], limit=10)
    expenses = get_expenses(user['id'], limit=10)
    businesses = get_businesses(user['id'])
    pnl = get_profit_loss(user['id'])

    return render_template_string("""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard - KenyaComply</title>
<style>""" + BASE_CSS + """
.welcome { margin-bottom:20px; }
.kra-pin { background:#fff3cd; padding:8px 15px; border-radius:8px; font-size:0.9rem; margin-top:10px; }
.list-item { background:#f8f9fa; padding:12px 15px; border-radius:8px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; }
.actions-row { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:20px; }
</style></head><body>
""" + NAVBAR_HTML + """
<div class="container">
<div class="card welcome">
    <h2>Welcome, {{ user.name or user.email }}</h2>
    {% if user.kra_pin %}<div class="kra-pin">KRA PIN: <strong>{{ user.kra_pin }}</strong> | Plan: <span class="badge badge-green">{{ user.plan|upper }}</span></div>
    {% else %}<div class="kra-pin">No KRA PIN saved. <a href="/settings">Update profile</a></div>{% endif %}
</div>

<div class="actions-row">
    <a href="/invoices" class="btn btn-primary btn-sm">New Invoice</a>
    <a href="/tax-returns" class="btn btn-green btn-sm">File Tax Return</a>
    <a href="/payroll" class="btn btn-blue btn-sm">Run Payroll</a>
    <a href="/expenses" class="btn btn-primary btn-sm">Add Expense</a>
    <a href="/pay" class="btn btn-mpesa btn-sm">M-Pesa Pay</a>
    <a href="/businesses" class="btn btn-outline btn-sm">My Businesses</a>
</div>

<div class="card">
    <h2>Overview</h2>
    <div class="stat-grid">
        <div class="stat"><div class="stat-value">{{ invoices|length }}</div><div class="stat-label">Invoices</div></div>
        <div class="stat"><div class="stat-value">{{ returns|length }}</div><div class="stat-label">Tax Returns</div></div>
        <div class="stat"><div class="stat-value">{{ payments|length }}</div><div class="stat-label">Payments</div></div>
        <div class="stat"><div class="stat-value">{{ expenses|length }}</div><div class="stat-label">Expenses</div></div>
        <div class="stat"><div class="stat-value">KES {{ "{:,.0f}".format(pnl.total_revenue) }}</div><div class="stat-label">Revenue</div></div>
        <div class="stat"><div class="stat-value">KES {{ "{:,.0f}".format(pnl.gross_profit) }}</div><div class="stat-label">Profit</div></div>
    </div>
</div>

<div class="card">
    <h2>Recent Invoices</h2>
    {% for inv in invoices[:5] %}
    <div class="list-item">
        <div><strong>{{ inv.invoice_number }}</strong> | {{ inv.buyer_name }} | {{ inv.date }}</div>
        <div><span class="badge badge-green">KES {{ "{:,.0f}".format(inv.total|float) }}</span></div>
    </div>
    {% else %}<p style="color:#666;">No invoices yet</p>{% endfor %}
</div>

<div class="card">
    <h2>Recent Payments</h2>
    {% for p in payments[:5] %}
    <div class="list-item">
        <div>{{ p.description or 'Payment' }} | {{ p.phone }}</div>
        <div><span class="badge badge-blue">KES {{ "{:,.0f}".format(p.amount|float) }}</span> <span class="badge badge-green">{{ p.status }}</span></div>
    </div>
    {% else %}<p style="color:#666;">No payments yet</p>{% endfor %}
</div>
</div>
""" + FOOTER_HTML + "</body></html>",
    user=user, invoices=invoices, payments=payments, returns=returns,
    expenses=expenses, businesses=businesses, pnl=pnl)

# ============================================
# INVOICES PAGE (multi-item, credit notes, recurring)
# ============================================
@app.route('/invoices')
def invoices_page():
    return render_template_string("""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Invoices - KenyaComply</title>
<style>""" + BASE_CSS + """
.item-row { background:#f8f9fa; padding:12px; border-radius:8px; margin-bottom:8px; }
.remove-btn { background:#d32f2f; color:white; border:none; padding:6px 12px; border-radius:6px; cursor:pointer; font-size:0.8rem; }
</style></head><body>
""" + NAVBAR_HTML + """
<div class="container">
<div class="card">
    <h2>Generate ETIMS Invoice</h2>
    <div class="tabs">
        <button class="tab active" onclick="showTab('standard',event)">Standard</button>
        <button class="tab" onclick="showTab('credit',event)">Credit Note</button>
        <button class="tab" onclick="showTab('debit',event)">Debit Note</button>
    </div>

    <form id="invoiceForm">
    <input type="hidden" name="invoice_type" id="invoiceType" value="standard">
    <div class="row">
        <div class="col form-group"><label>Seller Name</label><input type="text" name="seller_name" required placeholder="Your Company Ltd"></div>
        <div class="col form-group"><label>Seller KRA PIN</label><input type="text" name="seller_pin" required placeholder="P051234567A"></div>
    </div>
    <div class="row">
        <div class="col form-group"><label>Seller Phone</label><input type="tel" name="seller_phone" placeholder="+254700000000"></div>
        <div class="col form-group"><label>Seller Address</label><input type="text" name="seller_address" value="Nairobi, Kenya"></div>
    </div>
    <div class="row">
        <div class="col form-group"><label>Buyer Name</label><input type="text" name="buyer_name" required placeholder="Client Company Ltd"></div>
        <div class="col form-group"><label>Buyer KRA PIN</label><input type="text" name="buyer_pin" required placeholder="P098765432B"></div>
    </div>

    <h3 style="margin:15px 0 10px;">Line Items</h3>
    <div id="itemsList">
        <div class="item-row">
            <div class="row">
                <div class="col form-group"><label>Description</label><input type="text" class="item-desc" required placeholder="Consulting Services"></div>
                <div class="col form-group"><label>Qty</label><input type="number" class="item-qty" value="1" min="1"></div>
                <div class="col form-group"><label>Unit Price (KES)</label><input type="number" class="item-price" required placeholder="50000" min="0"></div>
                <div class="col form-group"><label>VAT %</label><select class="item-vat"><option value="16">16% (Standard)</option><option value="8">8% (Petroleum)</option><option value="0">0% (Exempt/Zero)</option></select></div>
            </div>
        </div>
    </div>
    <button type="button" onclick="addItem()" class="btn btn-outline btn-sm" style="margin-bottom:15px;">+ Add Item</button>

    <div class="row">
        <div class="col form-group"><label>Recurring Invoice?</label><select name="is_recurring" id="isRecurring"><option value="no">No</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option><option value="quarterly">Quarterly</option></select></div>
        <div class="col form-group"><label>M-Pesa Phone (KES 50 fee)</label><input type="tel" name="phone" required placeholder="07XX XXX XXX"></div>
    </div>
    <button type="submit" class="btn btn-mpesa btn-full">Pay KES 50 & Generate Invoice</button>
    </form>
    <div id="invoiceResult" class="result hidden"></div>
</div>
</div>
""" + FOOTER_HTML + """
<script>""" + BASE_JS + """
document.querySelectorAll('.tab').forEach(t => {
    t.addEventListener('click', function() {
        const types = {'Standard':'standard','Credit Note':'credit','Debit Note':'debit'};
        document.getElementById('invoiceType').value = types[this.textContent] || 'standard';
    });
});

function addItem() {
    const list = document.getElementById('itemsList');
    const row = document.createElement('div');
    row.className = 'item-row';
    row.innerHTML = '<div class="row">' +
        '<div class="col form-group"><label>Description</label><input type="text" class="item-desc" placeholder="Service/Product"></div>' +
        '<div class="col form-group"><label>Qty</label><input type="number" class="item-qty" value="1" min="1"></div>' +
        '<div class="col form-group"><label>Unit Price</label><input type="number" class="item-price" placeholder="0" min="0"></div>' +
        '<div class="col form-group"><label>VAT %</label><select class="item-vat"><option value="16">16%</option><option value="8">8%</option><option value="0">0%</option></select></div>' +
        '<div style="padding-top:28px;"><button type="button" class="remove-btn" onclick="this.closest(\\'.item-row\\').remove()">Remove</button></div>' +
    '</div>';
    list.appendChild(row);
}

document.getElementById('invoiceForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const phone = fd.get('phone');
    const items = [];
    document.querySelectorAll('.item-row').forEach(row => {
        const desc = row.querySelector('.item-desc').value;
        const qty = parseFloat(row.querySelector('.item-qty').value) || 1;
        const price = parseFloat(row.querySelector('.item-price').value) || 0;
        const vat = parseFloat(row.querySelector('.item-vat').value);
        if (desc && price > 0) items.push({description:desc, quantity:qty, unit_price:price, vat_rate:vat});
    });
    if (!items.length) { alert('Add at least one item'); return; }
    const el = document.getElementById('invoiceResult');

    const paid = await mpesaPay(phone, 50, 'KenyaComply Invoice', el);
    if (!paid) return;

    const resp = await fetch('/api/invoice', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
            seller_name: fd.get('seller_name'), seller_pin: fd.get('seller_pin'),
            seller_phone: fd.get('seller_phone'), seller_address: fd.get('seller_address'),
            buyer_name: fd.get('buyer_name'), buyer_pin: fd.get('buyer_pin'),
            items: items, invoice_type: fd.get('invoice_type') || 'standard',
            is_recurring: fd.get('is_recurring') || 'no'
        })
    });
    const inv = await resp.json();
    el.innerHTML += '<h3>Invoice Generated</h3>' +
        '<div class="result-row"><span>Invoice #</span><span>'+inv.invoice_number+'</span></div>' +
        '<div class="result-row"><span>Date</span><span>'+inv.date+'</span></div>' +
        '<div class="result-row"><span>Items</span><span>'+inv.item_count+'</span></div>' +
        '<div class="result-row"><span>Subtotal</span><span>'+fmt(inv.subtotal)+'</span></div>' +
        '<div class="result-row"><span>VAT</span><span>'+fmt(inv.vat)+'</span></div>' +
        '<div class="result-row total"><span>Grand Total</span><span>'+fmt(inv.total)+'</span></div>' +
        '<div style="margin-top:12px;"><button class="btn btn-green btn-sm" onclick="download(\\''+inv.invoice_number+'.txt\\',`'+inv.download_text.replace(/`/g,'\\\\`')+'`)">Download</button></div>';
});
</script></body></html>""")

# ============================================
# TAX CALCULATORS PAGE
# ============================================
@app.route('/calculators')
def calculators_page():
    return render_template_string("""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tax Calculators - KenyaComply</title>
<style>""" + BASE_CSS + "</style></head><body>" + NAVBAR_HTML + """
<div class="container">
<h1 style="margin-bottom:20px;">Tax Calculators</h1>
<div class="tabs">
    <button class="tab active" onclick="showTab('calcPaye',event)">PAYE</button>
    <button class="tab" onclick="showTab('calcVat',event)">VAT</button>
    <button class="tab" onclick="showTab('calcCorp',event)">Corporate Tax</button>
    <button class="tab" onclick="showTab('calcTot',event)">Turnover Tax</button>
    <button class="tab" onclick="showTab('calcWht',event)">Withholding Tax</button>
</div>

<div id="calcPaye" class="tab-content card">
    <h2>PAYE Calculator (2024 Rates)</h2>
    <div class="form-group"><label>Gross Monthly Salary (KES)</label><input type="number" id="payeSalary" placeholder="100000"></div>
    <button class="btn btn-primary" onclick="calcPAYE()">Calculate</button>
    <div id="payeResult" class="result hidden"></div>
</div>

<div id="calcVat" class="tab-content card hidden">
    <h2>VAT Calculator (16%)</h2>
    <div class="form-group"><label>Output Sales (KES)</label><input type="number" id="vatSales" placeholder="500000"></div>
    <div class="row">
        <div class="col form-group"><label>Exempt Sales</label><input type="number" id="vatExempt" value="0"></div>
        <div class="col form-group"><label>Input VAT</label><input type="number" id="vatInput" value="0"></div>
    </div>
    <button class="btn btn-primary" onclick="calcVAT()">Calculate</button>
    <div id="vatResult" class="result hidden"></div>
</div>

<div id="calcCorp" class="tab-content card hidden">
    <h2>Corporate Tax Calculator</h2>
    <div class="form-group"><label>Gross Income (KES)</label><input type="number" id="corpIncome" placeholder="5000000"></div>
    <div class="row">
        <div class="col form-group"><label>Allowable Expenses</label><input type="number" id="corpExpenses" value="0"></div>
        <div class="col form-group"><label>Installments Paid</label><input type="number" id="corpInstallments" value="0"></div>
    </div>
    <div class="form-group"><label><input type="checkbox" id="corpSme"> SME (turnover < KES 500M) — 25% rate</label></div>
    <button class="btn btn-primary" onclick="calcCorp()">Calculate</button>
    <div id="corpResult" class="result hidden"></div>
</div>

<div id="calcTot" class="tab-content card hidden">
    <h2>Turnover Tax (TOT) Calculator</h2>
    <div class="alert alert-info">For businesses with annual turnover below KES 25M. Rate: 3%</div>
    <div class="form-group"><label>Gross Turnover (KES)</label><input type="number" id="totTurnover" placeholder="2000000"></div>
    <button class="btn btn-primary" onclick="calcTOT()">Calculate</button>
    <div id="totResult" class="result hidden"></div>
</div>

<div id="calcWht" class="tab-content card hidden">
    <h2>Withholding Tax Calculator</h2>
    <div class="form-group"><label>Payment Type</label><select id="whtType">
        <option value="dividends_resident">Dividends (Resident) - 5%</option>
        <option value="dividends_non_resident">Dividends (Non-Resident) - 15%</option>
        <option value="interest_resident">Interest (Resident) - 15%</option>
        <option value="royalties_resident">Royalties (Resident) - 5%</option>
        <option value="royalties_non_resident">Royalties (Non-Resident) - 20%</option>
        <option value="management_fees_resident">Management Fees (Resident) - 5%</option>
        <option value="management_fees_non_resident">Management Fees (Non-Resident) - 20%</option>
        <option value="professional_fees_resident">Professional Fees (Resident) - 5%</option>
        <option value="contractual_fees_resident">Contractual Fees (Resident) - 3%</option>
        <option value="rent_resident">Rent (Resident) - 10%</option>
        <option value="insurance_commission">Insurance Commission - 10%</option>
    </select></div>
    <div class="form-group"><label>Gross Amount (KES)</label><input type="number" id="whtAmount" placeholder="100000"></div>
    <button class="btn btn-primary" onclick="calcWHT()">Calculate</button>
    <div id="whtResult" class="result hidden"></div>
</div>
</div>
""" + FOOTER_HTML + """
<script>""" + BASE_JS + """
async function calcPAYE() {
    const s = parseFloat(document.getElementById('payeSalary').value)||0;
    const r = await (await fetch('/api/paye',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({salary:s})})).json();
    document.getElementById('payeResult').innerHTML = '<h3>PAYE Breakdown</h3>'+
        '<div class="result-row"><span>Gross</span><span>'+fmt(r.gross_salary)+'</span></div>'+
        '<div class="result-row"><span>NSSF</span><span>'+fmt(r.nssf)+'</span></div>'+
        '<div class="result-row"><span>Taxable</span><span>'+fmt(r.taxable_income)+'</span></div>'+
        '<div class="result-row"><span>Tax Before Relief</span><span>'+fmt(r.tax_before_relief)+'</span></div>'+
        '<div class="result-row"><span>Personal Relief</span><span>'+fmt(r.personal_relief)+'</span></div>'+
        '<div class="result-row"><span>PAYE</span><span>'+fmt(r.tax_after_relief)+'</span></div>'+
        '<div class="result-row"><span>NHIF</span><span>'+fmt(r.nhif)+'</span></div>'+
        '<div class="result-row total"><span>NET SALARY</span><span>'+fmt(r.net_salary)+'</span></div>';
    document.getElementById('payeResult').classList.remove('hidden');
}
async function calcVAT() {
    const d = {sales:parseFloat(document.getElementById('vatSales').value)||0,exempt:parseFloat(document.getElementById('vatExempt').value)||0,input_vat:parseFloat(document.getElementById('vatInput').value)||0};
    const r = await (await fetch('/api/vat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
    document.getElementById('vatResult').innerHTML = '<h3>VAT</h3>'+
        '<div class="result-row"><span>Sales</span><span>'+fmt(r.gross_sales)+'</span></div>'+
        '<div class="result-row"><span>VAT Collected</span><span>'+fmt(r.vat_collected)+'</span></div>'+
        '<div class="result-row"><span>Input VAT</span><span>'+fmt(r.input_vat)+'</span></div>'+
        '<div class="result-row total"><span>NET VAT</span><span>'+fmt(r.net_vat_payable)+'</span></div>';
    document.getElementById('vatResult').classList.remove('hidden');
}
async function calcCorp() {
    const d = {income:parseFloat(document.getElementById('corpIncome').value)||0,expenses:parseFloat(document.getElementById('corpExpenses').value)||0,installments:parseFloat(document.getElementById('corpInstallments').value)||0,is_sme:document.getElementById('corpSme').checked};
    const r = await (await fetch('/api/corporate-tax',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
    document.getElementById('corpResult').innerHTML = '<h3>Corporate Tax</h3>'+
        '<div class="result-row"><span>Gross Income</span><span>'+fmt(r.gross_income)+'</span></div>'+
        '<div class="result-row"><span>Expenses</span><span>'+fmt(r.allowable_expenses)+'</span></div>'+
        '<div class="result-row"><span>Taxable</span><span>'+fmt(r.taxable_income)+'</span></div>'+
        '<div class="result-row"><span>Rate</span><span>'+r.tax_rate+'%</span></div>'+
        '<div class="result-row"><span>Tax</span><span>'+fmt(r.tax_payable)+'</span></div>'+
        '<div class="result-row total"><span>Balance Due</span><span>'+fmt(r.balance_due)+'</span></div>';
    document.getElementById('corpResult').classList.remove('hidden');
}
async function calcTOT() {
    const t = parseFloat(document.getElementById('totTurnover').value)||0;
    const r = await (await fetch('/api/turnover-tax',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({turnover:t})})).json();
    document.getElementById('totResult').innerHTML = '<h3>Turnover Tax</h3>'+
        '<div class="result-row"><span>Turnover</span><span>'+fmt(r.gross_turnover)+'</span></div>'+
        '<div class="result-row"><span>Rate</span><span>'+r.tax_rate+'%</span></div>'+
        '<div class="result-row total"><span>TOT Payable</span><span>'+fmt(r.tax_payable)+'</span></div>';
    document.getElementById('totResult').classList.remove('hidden');
}
async function calcWHT() {
    const d = {amount:parseFloat(document.getElementById('whtAmount').value)||0,tax_type:document.getElementById('whtType').value};
    const r = await (await fetch('/api/withholding-tax',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})).json();
    document.getElementById('whtResult').innerHTML = '<h3>Withholding Tax</h3>'+
        '<div class="result-row"><span>Gross</span><span>'+fmt(r.gross_amount)+'</span></div>'+
        '<div class="result-row"><span>Type</span><span>'+r.tax_type+'</span></div>'+
        '<div class="result-row"><span>Rate</span><span>'+r.rate+'%</span></div>'+
        '<div class="result-row"><span>WHT</span><span>'+fmt(r.tax_amount)+'</span></div>'+
        '<div class="result-row total"><span>Net Amount</span><span>'+fmt(r.net_amount)+'</span></div>';
    document.getElementById('whtResult').classList.remove('hidden');
}
</script></body></html>""")

# ============================================
# TAX RETURNS PAGE
# ============================================
@app.route('/tax-returns')
def tax_returns_page():
    return render_template_string("""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tax Returns - KenyaComply</title>
<style>""" + BASE_CSS + """
.emp-row { background:#f8f9fa; padding:12px; border-radius:8px; margin-bottom:8px; }
</style></head><body>
""" + NAVBAR_HTML + """
<div class="container">
<h1 style="margin-bottom:5px;">File Tax Returns</h1>
<p style="color:#666; margin-bottom:20px;">KES 100 filing fee per return via M-Pesa</p>

<div class="tabs">
    <button class="tab active" onclick="showTab('rtIncome',event)">Income Tax</button>
    <button class="tab" onclick="showTab('rtPaye',event)">PAYE (P10)</button>
    <button class="tab" onclick="showTab('rtVat',event)">VAT</button>
    <button class="tab" onclick="showTab('rtCorp',event)">Corporate Tax</button>
    <button class="tab" onclick="showTab('rtTot',event)">Turnover Tax</button>
</div>

<!-- Income Tax -->
<div id="rtIncome" class="tab-content card">
    <h2>Income Tax Return (IT1)</h2>
    <div class="alert alert-info">Deadline: 30th June annually</div>
    <form id="incomeForm">
    <div class="form-group"><label>Tax Year</label><select name="tax_year"><option value="2025">2025</option><option value="2024" selected>2024</option><option value="2023">2023</option></select></div>
    <div class="form-group"><label>Annual Employment Income (KES)</label><input type="number" name="annual_income" required placeholder="1200000"></div>
    <div class="row"><div class="col form-group"><label>Other Income</label><input type="number" name="other_income" value="0"></div><div class="col form-group"><label>Deductions</label><input type="number" name="deductions" value="0"></div></div>
    <div class="row"><div class="col form-group"><label>PAYE Already Paid</label><input type="number" name="paye_already_paid" value="0"></div><div class="col form-group"><label>Withholding Tax Paid</label><input type="number" name="withholding_tax" value="0"></div></div>
    <div class="form-group"><label>M-Pesa Phone (KES 100)</label><input type="tel" name="phone" required placeholder="07XX XXX XXX"></div>
    <button type="submit" class="btn btn-mpesa btn-full">Pay KES 100 & Calculate</button>
    </form>
    <div id="incomeResult" class="result hidden"></div>
</div>

<!-- PAYE Return -->
<div id="rtPaye" class="tab-content card hidden">
    <h2>PAYE Return (P10)</h2>
    <div class="alert alert-info">Deadline: 9th of following month</div>
    <form id="payeReturnForm">
    <div class="form-group"><label>Period</label><select name="period" id="payePeriod">
        <option>January 2025</option><option>February 2025</option><option selected>March 2025</option>
        <option>April 2025</option><option>May 2025</option><option>June 2025</option>
        <option>July 2025</option><option>August 2025</option><option>September 2025</option>
        <option>October 2025</option><option>November 2025</option><option>December 2025</option>
    </select></div>
    <div id="employeeList"><div class="emp-row"><div class="row">
        <div class="col form-group"><label>Name</label><input type="text" class="emp-name" placeholder="John Doe"></div>
        <div class="col form-group"><label>KRA PIN</label><input type="text" class="emp-pin" placeholder="A123456789B"></div>
        <div class="col form-group"><label>Gross Salary</label><input type="number" class="emp-gross" placeholder="100000"></div>
    </div></div></div>
    <button type="button" onclick="addEmp()" class="btn btn-outline btn-sm" style="margin-bottom:12px;">+ Add Employee</button>
    <div class="form-group"><label>M-Pesa Phone (KES 100)</label><input type="tel" name="phone" id="payePhone" required placeholder="07XX XXX XXX"></div>
    <button type="submit" class="btn btn-mpesa btn-full">Pay KES 100 & Calculate</button>
    </form>
    <div id="payeReturnResult" class="result hidden"></div>
</div>

<!-- VAT Return -->
<div id="rtVat" class="tab-content card hidden">
    <h2>VAT Return</h2>
    <div class="alert alert-info">Deadline: 20th of following month</div>
    <form id="vatReturnForm">
    <div class="form-group"><label>Period</label><select id="vatPeriod">
        <option>January 2025</option><option>February 2025</option><option selected>March 2025</option>
        <option>April 2025</option><option>May 2025</option><option>June 2025</option>
        <option>July 2025</option><option>August 2025</option><option>September 2025</option>
        <option>October 2025</option><option>November 2025</option><option>December 2025</option>
    </select></div>
    <div class="form-group"><label>Output Sales (KES)</label><input type="number" name="output_sales" required placeholder="500000"></div>
    <div class="row"><div class="col form-group"><label>Exempt Sales</label><input type="number" name="exempt_sales" value="0"></div><div class="col form-group"><label>Input VAT</label><input type="number" name="input_vat" value="0"></div></div>
    <div class="form-group"><label>M-Pesa Phone (KES 100)</label><input type="tel" name="phone" id="vatPhone" required placeholder="07XX XXX XXX"></div>
    <button type="submit" class="btn btn-mpesa btn-full">Pay KES 100 & Calculate</button>
    </form>
    <div id="vatReturnResult" class="result hidden"></div>
</div>

<!-- Corporate Tax Return -->
<div id="rtCorp" class="tab-content card hidden">
    <h2>Corporate Tax Return</h2>
    <div class="alert alert-info">Deadline: 6th month after year-end</div>
    <form id="corpReturnForm">
    <div class="row"><div class="col form-group"><label>Gross Income (KES)</label><input type="number" name="gross_income" required placeholder="10000000"></div><div class="col form-group"><label>Allowable Expenses</label><input type="number" name="expenses" value="0"></div></div>
    <div class="row"><div class="col form-group"><label>Installments Paid</label><input type="number" name="installments" value="0"></div><div class="col form-group"><label><input type="checkbox" name="is_sme"> SME (25% rate)</label></div></div>
    <div class="form-group"><label>M-Pesa Phone (KES 100)</label><input type="tel" name="phone" id="corpPhone" required placeholder="07XX XXX XXX"></div>
    <button type="submit" class="btn btn-mpesa btn-full">Pay KES 100 & Calculate</button>
    </form>
    <div id="corpReturnResult" class="result hidden"></div>
</div>

<!-- Turnover Tax Return -->
<div id="rtTot" class="tab-content card hidden">
    <h2>Turnover Tax Return</h2>
    <div class="alert alert-info">Deadline: 20th of following month. For businesses with turnover < KES 25M.</div>
    <form id="totReturnForm">
    <div class="form-group"><label>Period</label><select id="totPeriod">
        <option>January 2025</option><option>February 2025</option><option selected>March 2025</option>
        <option>April 2025</option><option>May 2025</option><option>June 2025</option>
        <option>July 2025</option><option>August 2025</option><option>September 2025</option>
        <option>October 2025</option><option>November 2025</option><option>December 2025</option>
    </select></div>
    <div class="form-group"><label>Gross Turnover (KES)</label><input type="number" name="turnover" required placeholder="2000000"></div>
    <div class="form-group"><label>M-Pesa Phone (KES 100)</label><input type="tel" name="phone" id="totPhone" required placeholder="07XX XXX XXX"></div>
    <button type="submit" class="btn btn-mpesa btn-full">Pay KES 100 & Calculate</button>
    </form>
    <div id="totReturnResult" class="result hidden"></div>
</div>
</div>
""" + FOOTER_HTML + """
<script>""" + BASE_JS + """
function addEmp() {
    const row = document.createElement('div'); row.className='emp-row';
    row.innerHTML='<div class="row"><div class="col form-group"><label>Name</label><input type="text" class="emp-name" placeholder="Name"></div><div class="col form-group"><label>KRA PIN</label><input type="text" class="emp-pin"></div><div class="col form-group"><label>Gross</label><input type="number" class="emp-gross"></div></div>';
    document.getElementById('employeeList').appendChild(row);
}
async function fileReturn(formId, resultId, getData) {
    const form = document.getElementById(formId);
    const fd = new FormData(form);
    const phone = fd.get('phone') || document.getElementById(resultId.replace('Result','Phone'))?.value;
    if (!phone || phone.replace(/\\s/g,'').length < 10) { alert('Enter M-Pesa phone'); return; }
    const el = document.getElementById(resultId);
    const paid = await mpesaPay(phone, 100, 'KenyaComply Tax Return', el);
    if (!paid) return;
    const data = getData(fd);
    const r = await (await fetch('/api/tax-return',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})).json();
    el.innerHTML += '<h3>'+r.return_type+'</h3>';
    if (r.employees) {
        r.employees.forEach(e => { el.innerHTML += '<div class="emp-row"><strong>'+e.name+'</strong> | Gross: '+fmt(e.gross)+' | PAYE: '+fmt(e.paye)+' | Net: '+fmt(e.net)+'</div>'; });
    }
    Object.entries(r).forEach(([k,v]) => {
        if (['status','filing_steps','employees','itax_url','ref','return_type'].includes(k)) return;
        if (typeof v === 'number') el.innerHTML += '<div class="result-row"><span>'+k.replace(/_/g,' ')+'</span><span>'+fmt(v)+'</span></div>';
        else if (typeof v === 'string' && v) el.innerHTML += '<div class="result-row"><span>'+k.replace(/_/g,' ')+'</span><span>'+v+'</span></div>';
    });
    if (r.filing_steps) {
        el.innerHTML += '<h4 style="margin-top:15px; color:#1565c0;">Steps to File on iTax:</h4><ol class="steps">'+r.filing_steps.map(s=>'<li>'+s+'</li>').join('')+'</ol>';
    }
    el.innerHTML += '<a href="https://itax.kra.go.ke" target="_blank" class="btn btn-blue" style="margin-top:12px;">Open iTax</a>';
}
document.getElementById('incomeForm').addEventListener('submit', e => { e.preventDefault(); fileReturn('incomeForm','incomeResult', fd => ({
    return_type:'income_tax', tax_year:fd.get('tax_year'), annual_income:parseFloat(fd.get('annual_income')||0),
    other_income:parseFloat(fd.get('other_income')||0), deductions:parseFloat(fd.get('deductions')||0),
    paye_already_paid:parseFloat(fd.get('paye_already_paid')||0), withholding_tax:parseFloat(fd.get('withholding_tax')||0)
})); });
document.getElementById('payeReturnForm').addEventListener('submit', e => { e.preventDefault();
    const emps=[]; document.querySelectorAll('.emp-row').forEach(r=>{const g=r.querySelector('.emp-gross')?.value; if(g) emps.push({name:r.querySelector('.emp-name').value,pin:r.querySelector('.emp-pin').value,gross:parseFloat(g)});});
    if(!emps.length){alert('Add employees');return;} fileReturn('payeReturnForm','payeReturnResult', fd=>({return_type:'paye',period:document.getElementById('payePeriod').value,employees:emps}));
});
document.getElementById('vatReturnForm').addEventListener('submit', e => { e.preventDefault(); fileReturn('vatReturnForm','vatReturnResult', fd=>({
    return_type:'vat', period:document.getElementById('vatPeriod').value,
    output_sales:parseFloat(fd.get('output_sales')||0), exempt_sales:parseFloat(fd.get('exempt_sales')||0), input_vat:parseFloat(fd.get('input_vat')||0)
})); });
document.getElementById('corpReturnForm').addEventListener('submit', e => { e.preventDefault(); fileReturn('corpReturnForm','corpReturnResult', fd=>({
    return_type:'corporate', gross_income:parseFloat(fd.get('gross_income')||0), expenses:parseFloat(fd.get('expenses')||0),
    installments:parseFloat(fd.get('installments')||0), is_sme:fd.get('is_sme')==='on'
})); });
document.getElementById('totReturnForm').addEventListener('submit', e => { e.preventDefault(); fileReturn('totReturnForm','totReturnResult', fd=>({
    return_type:'turnover', period:document.getElementById('totPeriod').value, turnover:parseFloat(fd.get('turnover')||0)
})); });
</script></body></html>""")

# ============================================
# EXPENSES PAGE
# ============================================
@app.route('/expenses')
def expenses_page():
    return render_template_string("""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Expenses - KenyaComply</title>
<style>""" + BASE_CSS + """
.import-zone { border:2px dashed #ccc; border-radius:12px; padding:30px; text-align:center; cursor:pointer; transition:all 0.2s; background:#fafafa; }
.import-zone:hover, .import-zone.dragover { border-color:#007bff; background:#f0f7ff; }
.import-zone input[type=file] { display:none; }
.preview-table { width:100%; border-collapse:collapse; margin:12px 0; font-size:13px; }
.preview-table th { background:#f0f0f0; padding:8px; text-align:left; border-bottom:2px solid #ddd; }
.preview-table td { padding:6px 8px; border-bottom:1px solid #eee; }
.preview-table tr:hover { background:#f8f9fa; }
.payment-badge { display:inline-block; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:600; }
.payment-badge.cash { background:#e8e8e8; color:#555; }
.payment-badge.mpesa { background:#4caf50; color:#fff; }
.payment-badge.card { background:#2196f3; color:#fff; }
.payment-badge.bank { background:#ff9800; color:#fff; }
.import-count { font-size:28px; font-weight:700; color:#28a745; }
.mpesa-msg { background:#f8f9fa; padding:10px; border-radius:8px; margin-bottom:6px; font-family:monospace; font-size:12px; white-space:pre-wrap; }
</style></head><body>
""" + NAVBAR_HTML + """
<div class="container">
<h1 style="margin-bottom:5px;">Expense Tracker</h1>
<p style="color:#666;margin-bottom:20px;">Track expenses manually, import bank statements, or paste M-Pesa messages</p>

<div class="tabs">
    <button class="tab active" onclick="showTab('tabManual',event)">Add Expense</button>
    <button class="tab" onclick="showTab('tabCSV',event)">Import Bank CSV</button>
    <button class="tab" onclick="showTab('tabMpesa',event)">M-Pesa Import</button>
    <button class="tab" onclick="showTab('tabList',event)">Expenses</button>
</div>

<!-- Manual Entry -->
<div id="tabManual" class="tab-content">
<div class="card">
    <h2>Add Expense</h2>
    <form id="expenseForm">
    <div class="row">
        <div class="col form-group"><label>Description</label><input type="text" name="description" required placeholder="Office supplies"></div>
        <div class="col form-group"><label>Category</label><select name="category">
            <option value="office">Office Supplies</option><option value="transport">Transport</option>
            <option value="utilities">Utilities</option><option value="rent">Rent</option>
            <option value="salaries">Salaries</option><option value="marketing">Marketing</option>
            <option value="professional">Professional Fees</option><option value="equipment">Equipment</option>
            <option value="materials">Raw Materials</option><option value="insurance">Insurance</option>
            <option value="food">Food & Meals</option><option value="fuel">Fuel</option>
            <option value="airtime">Airtime & Data</option><option value="general">General</option>
        </select></div>
    </div>
    <div class="row">
        <div class="col form-group"><label>Amount (KES)</label><input type="number" name="amount" required placeholder="5000" min="0" step="0.01"></div>
        <div class="col form-group"><label>VAT Amount (KES)</label><input type="number" name="vat_amount" value="0" min="0" step="0.01"></div>
    </div>
    <div class="row">
        <div class="col form-group"><label>Supplier</label><input type="text" name="supplier" placeholder="Supplier name"></div>
        <div class="col form-group"><label>Supplier KRA PIN</label><input type="text" name="supplier_pin" placeholder="For VAT offset"></div>
    </div>
    <div class="row">
        <div class="col form-group"><label>Payment Method</label><select name="payment_method" id="payMethod" onchange="toggleCardFields()">
            <option value="cash">Cash</option>
            <option value="mpesa">M-Pesa</option>
            <option value="card">Debit/Credit Card</option>
            <option value="bank">Bank Transfer</option>
        </select></div>
        <div class="col form-group"><label>Date</label><input type="date" name="date" value=\"""" + datetime.now().strftime('%Y-%m-%d') + """"></div>
    </div>
    <div id="cardFields" class="hidden">
        <div class="row">
            <div class="col form-group"><label>Card Last 4 Digits</label><input type="text" name="card_last4" maxlength="4" placeholder="1234"></div>
            <div class="col form-group"><label>Bank</label><select name="card_bank">
                <option value="">Select Bank</option>
                <option value="equity">Equity Bank</option><option value="kcb">KCB</option>
                <option value="coop">Co-operative Bank</option><option value="stanbic">Stanbic</option>
                <option value="ncba">NCBA</option><option value="dtb">DTB</option>
                <option value="absa">Absa Kenya</option><option value="standard_chartered">Standard Chartered</option>
                <option value="im_bank">I&M Bank</option><option value="family">Family Bank</option>
                <option value="other">Other</option>
            </select></div>
        </div>
    </div>
    <div id="mpesaRefField" class="hidden">
        <div class="form-group"><label>M-Pesa Reference</label><input type="text" name="mpesa_ref" placeholder="e.g. SJ12ABC456"></div>
    </div>
    <button type="submit" class="btn btn-primary btn-full">Save Expense</button>
    </form>
    <div id="expenseResult" class="result hidden"></div>
</div>
</div>

<!-- Bank CSV Import -->
<div id="tabCSV" class="tab-content hidden">
<div class="card">
    <h2>Import Bank/Card Statement</h2>
    <p style="color:#666;margin-bottom:16px;">Upload a CSV file from your bank (Equity, KCB, Stanbic, NCBA, Co-op, etc.) or card statement. We'll auto-detect columns and import transactions as expenses.</p>
    <div class="form-group"><label>Bank / Source</label><select id="csvBank">
        <option value="auto">Auto-Detect</option>
        <option value="equity">Equity Bank</option><option value="kcb">KCB</option>
        <option value="coop">Co-operative Bank</option><option value="stanbic">Stanbic</option>
        <option value="ncba">NCBA</option><option value="absa">Absa Kenya</option>
        <option value="standard_chartered">Standard Chartered</option>
        <option value="generic_card">Credit/Debit Card Statement</option>
    </select></div>
    <div class="import-zone" id="csvDropZone" onclick="document.getElementById('csvFile').click()">
        <div style="font-size:36px;margin-bottom:8px;">&#128196;</div>
        <strong>Drop CSV file here or click to browse</strong>
        <p style="color:#999;font-size:13px;margin-top:6px;">Supports .csv files from any Kenyan bank</p>
        <input type="file" id="csvFile" accept=".csv,.txt">
    </div>
    <div id="csvPreview" class="hidden" style="margin-top:16px;">
        <h3>Preview <span id="csvCount" style="color:#28a745;"></span></h3>
        <div style="overflow-x:auto;"><table class="preview-table" id="csvTable"></table></div>
        <div class="row" style="margin-top:12px;">
            <div class="col"><button class="btn btn-green btn-full" onclick="importCSV()">Import All Expenses</button></div>
            <div class="col"><button class="btn btn-outline btn-full" onclick="clearCSV()">Cancel</button></div>
        </div>
    </div>
    <div id="csvResult" class="hidden"></div>
</div>
<div class="card">
    <h3>Expected CSV Format</h3>
    <p style="color:#666;font-size:13px;">Most bank CSVs work automatically. If auto-detect fails, ensure your CSV has these columns:</p>
    <table class="preview-table">
        <tr><th>Date</th><th>Description</th><th>Amount</th><th>Type (optional)</th></tr>
        <tr><td>2026-04-01</td><td>NAIVAS SUPERMARKET</td><td>3,500.00</td><td>DEBIT</td></tr>
        <tr><td>2026-04-02</td><td>UBER TRIP</td><td>850.00</td><td>DEBIT</td></tr>
    </table>
</div>
</div>

<!-- M-Pesa Import -->
<div id="tabMpesa" class="tab-content hidden">
<div class="card">
    <h2>Import M-Pesa Transactions</h2>
    <p style="color:#666;margin-bottom:16px;">Paste your M-Pesa confirmation messages below. We'll extract the amount, recipient, date, and reference automatically.</p>
    <div class="form-group">
        <label>Paste M-Pesa Messages (one per line or separated by blank lines)</label>
        <textarea id="mpesaText" rows="8" placeholder="SJ12ABC456 Confirmed. Ksh3,500.00 sent to NAIVAS SUPERMARKET 0712345678 on 5/4/26 at 2:30 PM. New M-PESA balance is Ksh12,350.00.

RK98DEF789 Confirmed. Ksh850.00 paid to UBER BV. on 5/4/26 at 3:15 PM.Transaction cost, Ksh0.00. New M-PESA balance is Ksh11,500.00." style="font-family:monospace;font-size:13px;"></textarea>
    </div>
    <button class="btn btn-green btn-full" onclick="parseMpesa()">Parse M-Pesa Messages</button>
    <div id="mpesaPreview" class="hidden" style="margin-top:16px;">
        <h3>Parsed Transactions <span id="mpesaCount" style="color:#28a745;"></span></h3>
        <div id="mpesaParsed"></div>
        <div class="row" style="margin-top:12px;">
            <div class="col"><button class="btn btn-green btn-full" onclick="importMpesa()">Import All as Expenses</button></div>
            <div class="col"><button class="btn btn-outline btn-full" onclick="clearMpesa()">Cancel</button></div>
        </div>
    </div>
    <div id="mpesaResult" class="hidden"></div>
</div>
<div class="card">
    <h3>How to Get M-Pesa Messages</h3>
    <div style="color:#666;font-size:14px;">
        <p><strong>Option 1:</strong> Open your SMS app, search for "MPESA", copy and paste the messages.</p>
        <p style="margin-top:8px;"><strong>Option 2:</strong> Dial *334# on Safaricom &rarr; My Account &rarr; M-Pesa Statement &rarr; get PDF via email, then copy the transactions.</p>
        <p style="margin-top:8px;"><strong>Supported formats:</strong> "sent to", "paid to", "Buy Goods", "Paybill", "Withdraw"</p>
    </div>
</div>
</div>

<!-- Expense List -->
<div id="tabList" class="tab-content hidden">
<div class="card">
    <h2>Recent Expenses</h2>
    <div class="row" style="margin-bottom:12px;">
        <div class="col form-group"><label>Filter by Payment</label><select id="filterPay" onchange="loadExpenses()">
            <option value="">All</option><option value="cash">Cash</option><option value="mpesa">M-Pesa</option>
            <option value="card">Card</option><option value="bank">Bank</option>
        </select></div>
        <div class="col form-group"><label>Filter by Source</label><select id="filterSource" onchange="loadExpenses()">
            <option value="">All</option><option value="manual">Manual</option><option value="csv_import">Bank CSV</option><option value="mpesa_import">M-Pesa Import</option>
        </select></div>
    </div>
    <div id="expenseList"><p style="color:#666;">Loading...</p></div>
</div>
<div class="card">
    <h2>Summary</h2>
    <div id="expenseSummary"></div>
</div>
</div>
</div>

<script>""" + BASE_JS + """
function showTab(id, e) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(id).classList.remove('hidden');
    if(e) e.target.classList.add('active');
    if(id === 'tabList') loadExpenses();
}

function toggleCardFields() {
    const m = document.getElementById('payMethod').value;
    document.getElementById('cardFields').classList.toggle('hidden', m !== 'card');
    document.getElementById('mpesaRefField').classList.toggle('hidden', m !== 'mpesa');
}

// ---- Manual entry ----
document.getElementById('expenseForm').addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = Object.fromEntries(fd);
    data.amount = parseFloat(data.amount)||0;
    data.vat_amount = parseFloat(data.vat_amount)||0;
    data.import_source = 'manual';
    const r = await (await fetch('/api/expenses',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})).json();
    document.getElementById('expenseResult').innerHTML = '<div class="alert alert-success">Expense saved!</div>';
    document.getElementById('expenseResult').classList.remove('hidden');
    e.target.reset(); toggleCardFields();
});

// ---- CSV Import ----
let csvRows = [];
const csvZone = document.getElementById('csvDropZone');
csvZone.addEventListener('dragover', e => { e.preventDefault(); csvZone.classList.add('dragover'); });
csvZone.addEventListener('dragleave', () => csvZone.classList.remove('dragover'));
csvZone.addEventListener('drop', e => { e.preventDefault(); csvZone.classList.remove('dragover'); handleCSVFile(e.dataTransfer.files[0]); });
document.getElementById('csvFile').addEventListener('change', e => { if(e.target.files[0]) handleCSVFile(e.target.files[0]); });

function handleCSVFile(file) {
    const reader = new FileReader();
    reader.onload = e => parseCSV(e.target.result);
    reader.readAsText(file);
}

function parseCSV(text) {
    const lines = text.trim().split('\\n').map(l => l.trim()).filter(l => l);
    if(lines.length < 2) { alert('CSV file is empty or has no data rows'); return; }

    // Parse header
    const sep = lines[0].includes('\\t') ? '\\t' : ',';
    const headers = lines[0].split(sep).map(h => h.replace(/"/g,'').trim().toLowerCase());

    // Auto-detect columns
    const dateCol = headers.findIndex(h => /date|time|posted|trans.*date|value.*date/.test(h));
    const descCol = headers.findIndex(h => /desc|narr|particular|detail|merchant|payee|reference/.test(h));
    const amtCol = headers.findIndex(h => /amount|debit|withdrawal|paid|money.*out|dr/.test(h));
    const typeCol = headers.findIndex(h => /type|dr.*cr|transaction.*type/.test(h));

    if(dateCol === -1 && descCol === -1 && amtCol === -1) {
        // Try treating as: date, description, amount
        if(headers.length >= 3) {
            parseCSVRows(lines.slice(1), sep, 0, 1, 2, -1);
            return;
        }
        alert('Could not detect columns. Ensure CSV has Date, Description, Amount columns.'); return;
    }

    parseCSVRows(lines.slice(1), sep, dateCol, descCol, amtCol, typeCol);
}

function parseCSVRows(lines, sep, dateIdx, descIdx, amtIdx, typeIdx) {
    csvRows = [];
    const bank = document.getElementById('csvBank').value;
    for(const line of lines) {
        const cols = line.split(sep).map(c => c.replace(/"/g,'').trim());
        if(cols.length < 3) continue;

        let amt = (cols[amtIdx]||'0').replace(/[^0-9.-]/g,'');
        amt = parseFloat(amt) || 0;
        if(amt <= 0) continue; // skip credits/zero

        // Skip if type column says CREDIT
        if(typeIdx >= 0) {
            const t = (cols[typeIdx]||'').toUpperCase();
            if(t === 'CREDIT' || t === 'CR') continue;
        }

        const desc = cols[descIdx] || 'Bank transaction';
        const dateStr = cols[dateIdx] || '';
        const cat = autoCategory(desc);

        csvRows.push({
            date: normalizeDate(dateStr),
            description: desc,
            amount: amt,
            category: cat,
            payment_method: bank === 'generic_card' ? 'card' : 'bank',
            card_bank: bank !== 'auto' && bank !== 'generic_card' ? bank : '',
            import_source: 'csv_import',
            vat_amount: 0
        });
    }

    if(!csvRows.length) { alert('No debit transactions found in CSV'); return; }

    // Show preview
    document.getElementById('csvCount').textContent = '(' + csvRows.length + ' transactions)';
    let html = '<tr><th>Date</th><th>Description</th><th>Category</th><th>Amount</th></tr>';
    csvRows.forEach(r => {
        html += '<tr><td>'+r.date+'</td><td>'+r.description+'</td><td>'+r.category+'</td><td style="text-align:right;">KES '+Number(r.amount).toLocaleString()+'</td></tr>';
    });
    document.getElementById('csvTable').innerHTML = html;
    document.getElementById('csvPreview').classList.remove('hidden');
}

function normalizeDate(d) {
    if(!d) return new Date().toISOString().slice(0,10);
    // Try various formats
    const parts = d.match(/(\\d{1,4})[\\/-](\\d{1,2})[\\/-](\\d{1,4})/);
    if(parts) {
        let [,a,b,c] = parts;
        if(a.length === 4) return a+'-'+b.padStart(2,'0')+'-'+c.padStart(2,'0');
        if(c.length === 4) return c+'-'+b.padStart(2,'0')+'-'+a.padStart(2,'0');
        if(parseInt(c) < 100) c = '20'+c;
        return c+'-'+b.padStart(2,'0')+'-'+a.padStart(2,'0');
    }
    return new Date().toISOString().slice(0,10);
}

function autoCategory(desc) {
    const d = desc.toUpperCase();
    if(/UBER|BOLT|TAXI|BUS|MATATU|SGR|KENYA AIRWAYS|FLY/.test(d)) return 'transport';
    if(/FUEL|SHELL|TOTAL|RUBIS|PETROL|DIESEL/.test(d)) return 'fuel';
    if(/NAIVAS|CARREFOUR|QUICKMART|TUSKYS|CHANDARANA|FOOD|RESTAURANT|CAFE|JAVA|KFC|CHICKEN/.test(d)) return 'food';
    if(/SAFARICOM|AIRTEL|TELKOM|AIRTIME|DATA|BUNDLE/.test(d)) return 'airtime';
    if(/KPLC|KENYA POWER|WATER|NAIROBI.*WATER|ELECTRICITY/.test(d)) return 'utilities';
    if(/RENT|LANDLORD/.test(d)) return 'rent';
    if(/INSURANCE|NHIF|BRITAM|JUBILEE|UAP/.test(d)) return 'insurance';
    if(/MARKETING|GOOGLE.*ADS|FACEBOOK|META|ADVERT/.test(d)) return 'marketing';
    if(/JUMIA|KILIMALL|OFFICE|STATIONERY/.test(d)) return 'office';
    return 'general';
}

async function importCSV() {
    if(!csvRows.length) return;
    const r = await (await fetch('/api/expenses/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({expenses:csvRows})})).json();
    document.getElementById('csvResult').innerHTML = '<div class="alert alert-success"><span class="import-count">'+r.imported+'</span> expenses imported from bank statement!</div>';
    document.getElementById('csvResult').classList.remove('hidden');
    document.getElementById('csvPreview').classList.add('hidden');
    csvRows = [];
}

function clearCSV() { csvRows = []; document.getElementById('csvPreview').classList.add('hidden'); }

// ---- M-Pesa Import ----
let mpesaRows = [];

function parseMpesa() {
    const text = document.getElementById('mpesaText').value.trim();
    if(!text) { alert('Paste M-Pesa messages first'); return; }

    mpesaRows = [];
    // Split by transaction code pattern (2 uppercase letters followed by alphanumeric)
    const msgs = text.split(/(?=\\b[A-Z]{2,3}[A-Z0-9]{7,10}\\s+Confirmed)/i);

    for(const msg of msgs) {
        const m = msg.trim();
        if(!m) continue;

        // Extract reference code
        const refMatch = m.match(/^([A-Z0-9]{8,13})\s+Confirmed/i);
        if(!refMatch) continue;
        const ref = refMatch[1];

        // Extract amount
        const amtMatch = m.match(/Ksh([0-9,.]+)/i);
        if(!amtMatch) continue;
        const amount = parseFloat(amtMatch[1].replace(/,/g,''));
        if(!amount || amount <= 0) continue;

        // Extract recipient
        let recipient = 'M-Pesa Transaction';
        const sentTo = m.match(/sent to ([A-Z0-9 .&'-]+?)(?:\\s+\\d|\\s+on\\s)/i);
        const paidTo = m.match(/paid to ([A-Z0-9 .&'-]+?)(?:\\.|\\s+on\\s)/i);
        const buyGoods = m.match(/Buy Goods.*?(?:from|to)\\s+([A-Z0-9 .&'-]+)/i);
        const paybill = m.match(/(?:Paybill|Pay Bill).*?([A-Z0-9 .&'-]+)/i);
        if(sentTo) recipient = sentTo[1].trim();
        else if(paidTo) recipient = paidTo[1].trim();
        else if(buyGoods) recipient = buyGoods[1].trim();
        else if(paybill) recipient = paybill[1].trim();

        // Extract date
        let date = new Date().toISOString().slice(0,10);
        const dateMatch = m.match(/on\\s+(\\d{1,2})[\\/-](\\d{1,2})[\\/-](\\d{2,4})/i);
        if(dateMatch) {
            let [,d,mo,y] = dateMatch;
            if(y.length === 2) y = '20'+y;
            date = y+'-'+mo.padStart(2,'0')+'-'+d.padStart(2,'0');
        }

        const cat = autoCategory(recipient);

        mpesaRows.push({
            date: date,
            description: recipient,
            amount: amount,
            category: cat,
            payment_method: 'mpesa',
            mpesa_ref: ref,
            supplier: recipient,
            import_source: 'mpesa_import',
            vat_amount: 0
        });
    }

    if(!mpesaRows.length) { alert('Could not parse any M-Pesa transactions. Make sure you paste the full confirmation messages.'); return; }

    document.getElementById('mpesaCount').textContent = '(' + mpesaRows.length + ' transactions)';
    let html = '';
    mpesaRows.forEach(r => {
        html += '<div style="background:#f8f9fa;padding:12px;border-radius:8px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">'+
            '<div><strong>'+r.description+'</strong><br><span style="color:#666;font-size:12px;">'+r.mpesa_ref+' | '+r.date+' | '+r.category+'</span></div>'+
            '<div><span class="badge badge-green" style="font-size:14px;">KES '+Number(r.amount).toLocaleString()+'</span></div></div>';
    });
    document.getElementById('mpesaParsed').innerHTML = html;
    document.getElementById('mpesaPreview').classList.remove('hidden');
}

async function importMpesa() {
    if(!mpesaRows.length) return;
    const r = await (await fetch('/api/expenses/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({expenses:mpesaRows})})).json();
    document.getElementById('mpesaResult').innerHTML = '<div class="alert alert-success"><span class="import-count">'+r.imported+'</span> M-Pesa expenses imported!</div>';
    document.getElementById('mpesaResult').classList.remove('hidden');
    document.getElementById('mpesaPreview').classList.add('hidden');
    mpesaRows = []; document.getElementById('mpesaText').value = '';
}

function clearMpesa() { mpesaRows = []; document.getElementById('mpesaPreview').classList.add('hidden'); }

// ---- Expense List ----
async function loadExpenses() {
    const payFilter = document.getElementById('filterPay')?.value || '';
    const srcFilter = document.getElementById('filterSource')?.value || '';
    const r = await (await fetch('/api/expenses')).json();
    const list = document.getElementById('expenseList');
    if (!r.expenses || !r.expenses.length) { list.innerHTML='<p style="color:#666;">No expenses yet</p>'; return; }

    let exps = r.expenses;
    if(payFilter) exps = exps.filter(e => e.payment_method === payFilter);
    if(srcFilter) exps = exps.filter(e => e.import_source === srcFilter);

    const payBadge = m => {
        const labels = {cash:'Cash',mpesa:'M-Pesa',card:'Card',bank:'Bank'};
        return '<span class="payment-badge '+(m||'cash')+'">'+(labels[m]||'Cash')+'</span>';
    };

    list.innerHTML = exps.map(e => '<div style="background:#f8f9fa;padding:12px;border-radius:8px;margin-bottom:8px;display:flex;justify-content:space-between;flex-wrap:wrap;align-items:center;">'+
        '<div><strong>'+e.description+'</strong><br><span style="color:#666;font-size:12px;">'+e.category+' | '+(e.date||'')+
        (e.card_last4?' | ****'+e.card_last4:'')+
        (e.mpesa_ref?' | '+e.mpesa_ref:'')+
        (e.card_bank?' | '+e.card_bank:'')+
        '</span></div>'+
        '<div style="text-align:right;">'+payBadge(e.payment_method)+' <span class="badge badge-blue">KES '+fmt(e.amount)+'</span>'+
        (e.vat_amount>0?' <span class="badge badge-green">VAT: '+fmt(e.vat_amount)+'</span>':'')+'</div></div>'
    ).join('');

    const s = r.summary;
    document.getElementById('expenseSummary').innerHTML =
        '<div class="stat-grid"><div class="stat"><div class="stat-value">'+s.count+'</div><div class="stat-label">Expenses</div></div>'+
        '<div class="stat"><div class="stat-value">'+fmt(s.total)+'</div><div class="stat-label">Total Spent</div></div>'+
        '<div class="stat"><div class="stat-value">'+fmt(s.total_vat)+'</div><div class="stat-label">Input VAT</div></div></div>';
}
loadExpenses();
</script>
""" + FOOTER_HTML + "</body></html>""")

# ============================================
# PAYROLL PAGE
# ============================================
@app.route('/payroll')
def payroll_page():
    return render_template_string("""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Payroll - KenyaComply</title>
<style>""" + BASE_CSS + """
.emp-row { background:#f8f9fa; padding:12px; border-radius:8px; margin-bottom:8px; }
.payslip { background:#f0f7f0; padding:15px; border-radius:8px; margin-bottom:10px; border-left:4px solid #2e7d32; }
</style></head><body>
""" + NAVBAR_HTML + """
<div class="container">
<h1 style="margin-bottom:5px;">Payroll</h1>
<p style="color:#666; margin-bottom:20px;">Monthly salary processing with auto PAYE/NSSF/NHIF. KES 150 per payroll run.</p>

<div class="tabs">
    <button class="tab active" onclick="showTab('runPayroll',event)">Run Payroll</button>
    <button class="tab" onclick="showTab('p9Form',event)">P9 Form</button>
</div>

<div id="runPayroll" class="tab-content card">
    <h2>Run Monthly Payroll</h2>
    <form id="payrollForm">
    <div id="payrollEmps">
        <div class="emp-row"><div class="row">
            <div class="col form-group"><label>Name</label><input type="text" class="pr-name" required placeholder="John Doe"></div>
            <div class="col form-group"><label>KRA PIN</label><input type="text" class="pr-pin" placeholder="A123456789B"></div>
            <div class="col form-group"><label>Gross Salary</label><input type="number" class="pr-gross" required placeholder="100000"></div>
            <div class="col form-group"><label>Allowances</label><input type="number" class="pr-allow" value="0"></div>
        </div></div>
    </div>
    <button type="button" onclick="addPrEmp()" class="btn btn-outline btn-sm" style="margin-bottom:12px;">+ Add Employee</button>
    <div class="form-group"><label>M-Pesa Phone (KES 150)</label><input type="tel" name="phone" required placeholder="07XX XXX XXX"></div>
    <button type="submit" class="btn btn-mpesa btn-full">Pay KES 150 & Process Payroll</button>
    </form>
    <div id="payrollResult" class="result hidden"></div>
</div>

<div id="p9Form" class="tab-content card hidden">
    <h2>Generate P9 Form</h2>
    <div class="alert alert-info">P9 form summarizes annual PAYE deductions. Employers must issue to employees by end of February. KES 100 per form.</div>
    <form id="p9Form2">
    <div class="row">
        <div class="col form-group"><label>Employee Name</label><input type="text" name="emp_name" required placeholder="John Doe"></div>
        <div class="col form-group"><label>KRA PIN</label><input type="text" name="emp_pin" required placeholder="A123456789B"></div>
    </div>
    <div class="form-group"><label>Monthly Gross Salary (same for all 12 months)</label><input type="number" name="monthly_gross" required placeholder="100000"></div>
    <div class="form-group"><label>M-Pesa Phone (KES 100)</label><input type="tel" name="phone" required placeholder="07XX XXX XXX"></div>
    <button type="submit" class="btn btn-mpesa btn-full">Pay KES 100 & Generate P9</button>
    </form>
    <div id="p9Result" class="result hidden"></div>
</div>
</div>
""" + FOOTER_HTML + """
<script>""" + BASE_JS + """
function addPrEmp() {
    const row = document.createElement('div'); row.className='emp-row';
    row.innerHTML='<div class="row"><div class="col form-group"><label>Name</label><input type="text" class="pr-name" placeholder="Name"></div><div class="col form-group"><label>KRA PIN</label><input type="text" class="pr-pin"></div><div class="col form-group"><label>Gross</label><input type="number" class="pr-gross"></div><div class="col form-group"><label>Allowances</label><input type="number" class="pr-allow" value="0"></div></div>';
    document.getElementById('payrollEmps').appendChild(row);
}
document.getElementById('payrollForm').addEventListener('submit', async e => {
    e.preventDefault();
    const phone = new FormData(e.target).get('phone');
    const emps = [];
    document.querySelectorAll('#payrollEmps .emp-row').forEach(r => {
        const g = r.querySelector('.pr-gross')?.value;
        if(g) emps.push({name:r.querySelector('.pr-name').value, kra_pin:r.querySelector('.pr-pin').value, gross_salary:parseFloat(g), allowances:parseFloat(r.querySelector('.pr-allow').value)||0});
    });
    if(!emps.length){alert('Add employees');return;}
    const el = document.getElementById('payrollResult');
    const paid = await mpesaPay(phone, 150, 'KenyaComply Payroll', el);
    if(!paid) return;
    const r = await (await fetch('/api/payroll',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({employees:emps})})).json();
    let html = '<h3>Payroll - '+r.period+'</h3>';
    r.payslips.forEach(p => {
        html += '<div class="payslip"><strong>'+p.name+'</strong> ('+p.kra_pin+')<br>'+
            'Gross: '+fmt(p.gross_salary)+' | NSSF: '+fmt(p.nssf)+' | PAYE: '+fmt(p.paye)+' | NHIF: '+fmt(p.nhif)+' | <strong>Net: '+fmt(p.net_salary)+'</strong></div>';
    });
    html += '<div class="result-row total"><span>Total PAYE</span><span>'+fmt(r.totals.paye)+'</span></div>';
    html += '<div class="result-row total"><span>Total Net Pay</span><span>'+fmt(r.totals.net)+'</span></div>';
    el.innerHTML += html;
});
document.getElementById('p9Form2').addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const phone = fd.get('phone');
    const el = document.getElementById('p9Result');
    const paid = await mpesaPay(phone, 100, 'KenyaComply P9', el);
    if(!paid) return;
    const r = await (await fetch('/api/p9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
        name:fd.get('emp_name'), kra_pin:fd.get('emp_pin'), monthly_gross:parseFloat(fd.get('monthly_gross'))
    })})).json();
    el.innerHTML += '<h3>P9 Form - '+r.employee_name+'</h3><div class="result-row"><span>KRA PIN</span><span>'+r.kra_pin+'</span></div><div class="result-row"><span>Tax Year</span><span>'+r.tax_year+'</span></div>';
    const a = r.annual_totals;
    el.innerHTML += '<div class="result-row"><span>Annual Gross</span><span>'+fmt(a.gross)+'</span></div><div class="result-row"><span>Annual PAYE</span><span>'+fmt(a.paye)+'</span></div><div class="result-row"><span>Annual NSSF</span><span>'+fmt(a.nssf)+'</span></div><div class="result-row"><span>Annual NHIF</span><span>'+fmt(a.nhif)+'</span></div>';
    el.innerHTML += '<div style="margin-top:12px;"><button class="btn btn-green btn-sm" onclick="download(\\'P9_'+r.kra_pin+'.txt\\',`'+r.download_text.replace(/`/g,'\\\\`')+'`)">Download P9</button></div>';
});
</script></body></html>""")

# ============================================
# M-PESA PAY PAGE
# ============================================
@app.route('/pay')
def pay_page():
    return render_template_string("""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>M-Pesa Pay - KenyaComply</title>
<style>""" + BASE_CSS + "</style></head><body>" + NAVBAR_HTML + """
<div class="container">
<div class="card">
    <h2>M-Pesa Payment (Lipa Na M-Pesa)</h2>
    <div class="alert alert-info"><strong>Safaricom STK Push</strong> - Enter phone and amount. You'll get an M-Pesa prompt to enter your PIN.</div>
    <form id="mpesaForm">
    <div class="form-group"><label>M-Pesa Phone Number</label><input type="tel" name="phone" required placeholder="0712 345 678"></div>
    <div class="form-group"><label>Amount (KES)</label><input type="number" name="amount" required placeholder="1000" min="1"></div>
    <div class="form-group"><label>Reference</label><input type="text" name="ref" value="KenyaComply"></div>
    <button type="submit" class="btn btn-mpesa btn-full">Send STK Push</button>
    </form>
    <div id="mpesaResult" class="result hidden"></div>
</div>
</div>
""" + FOOTER_HTML + """
<script>""" + BASE_JS + """
document.getElementById('mpesaForm').addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const el = document.getElementById('mpesaResult');
    const paid = await mpesaPay(fd.get('phone'), parseFloat(fd.get('amount')), fd.get('ref'), el);
});
</script></body></html>""")

# ============================================
# REPORTS PAGE (P&L)
# ============================================
@app.route('/reports')
def reports_page():
    return render_template_string("""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Reports - KenyaComply</title>
<style>""" + BASE_CSS + """
.pnl-row { display:flex; justify-content:space-between; padding:12px 0; border-bottom:1px solid #e0e0e0; }
.pnl-row.header { font-weight:bold; background:#f8f9fa; padding:12px; border-radius:6px; margin:5px 0; }
.pnl-row.profit { font-size:1.2rem; font-weight:bold; background:#e8f5e9; padding:12px; border-radius:6px; margin-top:10px; }
.pnl-row.loss { background:#f8d7da; }
</style></head><body>
""" + NAVBAR_HTML + """
<div class="container">
<h1 style="margin-bottom:20px;">Financial Reports</h1>
<div class="card">
    <h2>Profit & Loss Statement</h2>
    <div id="pnlReport"><p style="color:#666;">Loading...</p></div>
</div>
<div class="card">
    <h2>Expense Breakdown</h2>
    <div id="expenseBreakdown"></div>
</div>
</div>
""" + FOOTER_HTML + """
<script>""" + BASE_JS + """
async function loadReport() {
    const r = await (await fetch('/api/reports/pnl')).json();
    const el = document.getElementById('pnlReport');
    const profitClass = r.gross_profit >= 0 ? 'profit' : 'profit loss';
    el.innerHTML =
        '<div class="pnl-row header"><span>REVENUE</span><span></span></div>'+
        '<div class="pnl-row"><span>Total Sales ('+r.invoice_count+' invoices)</span><span>'+fmt(r.total_revenue)+'</span></div>'+
        '<div class="pnl-row"><span>VAT Collected</span><span>'+fmt(r.total_vat_collected)+'</span></div>'+
        '<div class="pnl-row header"><span>EXPENSES</span><span></span></div>'+
        '<div class="pnl-row"><span>Total Expenses ('+r.expense_count+' items)</span><span>'+fmt(r.total_expenses)+'</span></div>'+
        '<div class="pnl-row"><span>Input VAT</span><span>'+fmt(r.total_input_vat)+'</span></div>'+
        '<div class="pnl-row header"><span>VAT POSITION</span><span></span></div>'+
        '<div class="pnl-row"><span>Net VAT Payable</span><span>'+fmt(r.net_vat_payable)+'</span></div>'+
        '<div class="pnl-row '+profitClass+'"><span>GROSS PROFIT</span><span>'+fmt(r.gross_profit)+'</span></div>';
    const cats = r.expense_by_category || {};
    const catEl = document.getElementById('expenseBreakdown');
    if (Object.keys(cats).length === 0) { catEl.innerHTML = '<p style="color:#666;">No expenses recorded yet</p>'; return; }
    catEl.innerHTML = Object.entries(cats).sort((a,b)=>b[1]-a[1]).map(([k,v]) =>
        '<div class="pnl-row"><span>'+k.charAt(0).toUpperCase()+k.slice(1)+'</span><span>'+fmt(v)+'</span></div>'
    ).join('');
}
loadReport();
</script></body></html>""")

# ============================================
# BUSINESSES PAGE
# ============================================
@app.route('/businesses')
def businesses_page():
    return render_template_string("""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>My Businesses - KenyaComply</title>
<style>""" + BASE_CSS + "</style></head><body>" + NAVBAR_HTML + """
<div class="container">
<h1 style="margin-bottom:20px;">My Businesses</h1>
<div class="card">
    <h2>Add Business</h2>
    <form id="bizForm">
    <div class="row">
        <div class="col form-group"><label>Business Name</label><input type="text" name="name" required placeholder="My Company Ltd"></div>
        <div class="col form-group"><label>KRA PIN</label><input type="text" name="kra_pin" required placeholder="P051234567A"></div>
    </div>
    <div class="row">
        <div class="col form-group"><label>Type</label><select name="business_type"><option value="sole_proprietor">Sole Proprietor</option><option value="limited">Limited Company</option><option value="partnership">Partnership</option></select></div>
        <div class="col form-group"><label>Phone</label><input type="tel" name="phone" placeholder="0712345678"></div>
    </div>
    <div class="form-group"><label>Address</label><input type="text" name="address" placeholder="Nairobi, Kenya"></div>
    <button type="submit" class="btn btn-primary btn-full">Add Business</button>
    </form>
    <div id="bizResult" class="result hidden"></div>
</div>
<div class="card"><h2>My Businesses</h2><div id="bizList"><p style="color:#666;">Loading...</p></div></div>
</div>
""" + FOOTER_HTML + """
<script>""" + BASE_JS + """
async function loadBiz() {
    const r = await (await fetch('/api/businesses')).json();
    const el = document.getElementById('bizList');
    if (!r.businesses || !r.businesses.length) { el.innerHTML='<p style="color:#666;">No businesses added yet</p>'; return; }
    el.innerHTML = r.businesses.map(b => '<div style="background:#f8f9fa;padding:15px;border-radius:8px;margin-bottom:8px;"><strong>'+b.name+'</strong> | PIN: '+b.kra_pin+' | '+b.business_type+'</div>').join('');
}
document.getElementById('bizForm').addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = Object.fromEntries(fd);
    const r = await (await fetch('/api/businesses',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})).json();
    document.getElementById('bizResult').innerHTML = '<div class="alert alert-success">Business added!</div>';
    document.getElementById('bizResult').classList.remove('hidden');
    e.target.reset(); loadBiz();
});
loadBiz();
</script></body></html>""")

# ============================================
# SETTINGS PAGE
# ============================================
@app.route('/settings')
def settings_page():
    user = get_current_user()
    if not user:
        return redirect('/login')
    return render_template_string("""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Settings - KenyaComply</title>
<style>""" + BASE_CSS + "</style></head><body>" + NAVBAR_HTML + """
<div class="container">
<div class="card">
    <h2>Profile Settings</h2>
    <form method="POST" action="/api/settings">
    <div class="form-group"><label>Name</label><input type="text" name="name" value="{{ user.name }}"></div>
    <div class="form-group"><label>Email</label><input type="email" value="{{ user.email }}" disabled></div>
    <div class="row">
        <div class="col form-group"><label>KRA PIN</label><input type="text" name="kra_pin" value="{{ user.kra_pin or '' }}" placeholder="A123456789B"></div>
        <div class="col form-group"><label>Phone</label><input type="tel" name="phone" value="{{ user.phone or '' }}" placeholder="0712345678"></div>
    </div>
    <button type="submit" class="btn btn-primary">Save Changes</button>
    </form>
</div>
</div>
""" + FOOTER_HTML + "</body></html>", user=user)

@app.route('/api/settings', methods=['POST'])
def api_settings():
    user = get_current_user()
    if not user:
        return redirect('/login')
    update_user(user['id'], {
        'name': request.form.get('name', user['name']),
        'kra_pin': request.form.get('kra_pin', '').strip().upper(),
        'phone': request.form.get('phone', '').strip()
    })
    return redirect('/settings')

# ============================================
# iTAX GUIDE (comprehensive)
# ============================================
@app.route('/itax-guide')
def itax_guide():
    return render_template_string("""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>iTax Guide - KenyaComply</title>
<style>""" + BASE_CSS + """
.guide-section { margin-bottom:0; }
</style></head><body>
""" + NAVBAR_HTML + """
<div class="container">
<h1 style="margin-bottom:20px;">KRA iTax Filing Guide</h1>

<div class="card">
<h2>Tax Deadlines & Penalties</h2>
<table>
<tr><th>Tax</th><th>Who</th><th>Deadline</th><th>Penalty</th></tr>
<tr><td>Income Tax</td><td>Individuals</td><td style="color:#d32f2f;font-weight:bold;">30th June</td><td>KES 20,000 or 5%</td></tr>
<tr><td>PAYE</td><td>Employers</td><td style="color:#d32f2f;font-weight:bold;">9th next month</td><td>25% + 5%/month</td></tr>
<tr><td>VAT</td><td>Businesses >5M</td><td style="color:#d32f2f;font-weight:bold;">20th next month</td><td>KES 10,000 + 5%</td></tr>
<tr><td>Corporate Tax</td><td>Companies</td><td style="color:#d32f2f;font-weight:bold;">6mo after year-end</td><td>5% + 1%/month</td></tr>
<tr><td>Turnover Tax</td><td>Businesses <25M</td><td style="color:#d32f2f;font-weight:bold;">20th next month</td><td>KES 1,000/month</td></tr>
</table></div>

<div class="card"><h2>Filing Income Tax (IT1)</h2>
<div class="alert alert-warning">Need: KRA PIN, P9 form, bank interest certificates, rental income records</div>
<ol class="steps">
<li>Go to <strong>itax.kra.go.ke</strong> and log in</li>
<li>Click <strong>Returns > File Return > Income Tax Resident Individual</strong></li>
<li>Fill employment income from P9 form</li>
<li>Add other income (rental, business, interest)</li>
<li>Enter deductions (NSSF, insurance, mortgage, pension)</li>
<li>Review auto-calculated tax (personal relief KES 28,800/yr deducted)</li>
<li>Enter PAYE already deducted and withholding tax credits</li>
<li>Submit. Pay balance via M-Pesa Paybill <strong>572572</strong></li>
</ol>
<div class="alert alert-success">Use <a href="/tax-returns">Tax Return Calculator</a> to prepare figures before iTax.</div>
</div>

<div class="card"><h2>Filing PAYE (P10) - Employers</h2>
<ol class="steps">
<li>Log in to iTax with company KRA PIN</li>
<li><strong>Returns > File Return > PAYE</strong></li>
<li>Upload CSV or fill online for each employee</li>
<li>Verify total PAYE matches payroll</li>
<li>Submit and pay via Paybill <strong>572572</strong></li>
<li>Issue P9 forms to employees by end of February</li>
</ol></div>

<div class="card"><h2>Filing VAT Return</h2>
<ol class="steps">
<li>Log in to iTax</li>
<li><strong>Returns > File Return > VAT</strong></li>
<li>Enter output VAT (16% of taxable sales)</li>
<li>Enter input VAT (from valid tax invoices)</li>
<li>Submit and pay net VAT</li>
</ol>
<div class="alert alert-warning">Keep all ETIMS invoices for 5 years. Use KenyaComply to generate compliant invoices.</div>
</div>

<div class="card"><h2>M-Pesa Tax Payment</h2>
<ol class="steps">
<li>M-Pesa > Lipa na M-Pesa > Pay Bill</li>
<li>Business Number: <strong>572572</strong></li>
<li>Account: <strong>KRA PIN + Tax Code</strong></li>
<li>Enter amount and M-Pesa PIN</li>
</ol>
<table><tr><th>Tax</th><th>Account Format</th><th>Example</th></tr>
<tr><td>Income Tax</td><td>PIN + IT</td><td>A123456789BIT</td></tr>
<tr><td>PAYE</td><td>PIN + PAYE</td><td>A123456789BPAYE</td></tr>
<tr><td>VAT</td><td>PIN + VAT</td><td>A123456789BVAT</td></tr>
<tr><td>Corporate</td><td>PIN + CT</td><td>P123456789ACT</td></tr>
</table></div>

<div class="card"><h2>Nil Returns</h2>
<p>Even with no income, file a nil return to avoid KES 20,000 penalty.</p>
<ol class="steps"><li>Log in to iTax</li><li>Returns > File Return > Select "Nil Return"</li><li>Submit</li></ol></div>

<div class="card"><h2>KRA Contacts</h2>
<p><strong>Phone:</strong> 020-4-999-999 / 0711-099-999</p>
<p><strong>Email:</strong> callcentre@kra.go.ke</p>
<p><strong>WhatsApp:</strong> 0728-606-161</p>
<p><strong>Portal:</strong> <a href="https://itax.kra.go.ke" target="_blank">itax.kra.go.ke</a></p>
</div>
</div>
""" + FOOTER_HTML + "</body></html>")

# ============================================
# API ENDPOINTS
# ============================================

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

@app.route("/api/corporate-tax", methods=["POST"])
def api_corporate_tax():
    data = request.json
    result = calculate_corporate_tax(
        data.get("income", 0), data.get("expenses", 0),
        data.get("is_sme", False), data.get("installments", 0)
    )
    return jsonify({
        "gross_income": result.gross_income, "allowable_expenses": result.allowable_expenses,
        "taxable_income": result.taxable_income, "tax_rate": result.tax_rate,
        "tax_payable": result.tax_payable, "installments_paid": result.installments_paid,
        "balance_due": result.balance_due
    })

@app.route("/api/turnover-tax", methods=["POST"])
def api_turnover_tax():
    data = request.json
    result = calculate_turnover_tax(data.get("turnover", 0))
    return jsonify({
        "gross_turnover": result.gross_turnover, "tax_rate": result.tax_rate,
        "tax_payable": result.tax_payable
    })

@app.route("/api/withholding-tax", methods=["POST"])
def api_withholding_tax():
    data = request.json
    result = calculate_withholding_tax(data.get("amount", 0), data.get("tax_type", "professional_fees_resident"))
    return jsonify({
        "gross_amount": result.gross_amount, "tax_type": result.tax_type,
        "rate": result.rate, "tax_amount": result.tax_amount, "net_amount": result.net_amount
    })

@app.route("/api/invoice", methods=["POST"])
def api_invoice():
    data = request.json
    items = data.get("items", [{"description": "Service", "quantity": 1, "unit_price": data.get("amount", 0), "vat_rate": 16}])

    invoice = create_standard_invoice(
        seller_name=data.get("seller_name", ""),
        seller_pin=data.get("seller_pin", ""),
        seller_address=data.get("seller_address", "Nairobi, Kenya"),
        seller_phone=data.get("seller_phone", ""),
        buyer_name=data.get("buyer_name", ""),
        buyer_pin=data.get("buyer_pin", ""),
        buyer_address="Kenya",
        items=items
    )

    lines = [f"  {i['description']:30s} x{i['quantity']} @ {i['unit_price']:,.0f} ({i.get('vat_rate',16)}% VAT)" for i in items]
    invoice_text = f"""KENYACOMPLY ETIMS INVOICE
========================
Invoice #{invoice.invoice_number} | {invoice.date}
Type: {data.get('invoice_type','standard').upper()}

SELLER: {data.get('seller_name','')} | PIN: {data.get('seller_pin','')}
BUYER: {data.get('buyer_name','')} | PIN: {data.get('buyer_pin','')}

ITEMS:
{chr(10).join(lines)}

Subtotal: KES {invoice.subtotal:,.2f}
VAT: KES {invoice.total_vat:,.2f}
GRAND TOTAL: KES {invoice.grand_total:,.2f}

Generated by KenyaComply"""

    user = get_current_user()
    if user:
        save_invoice(user['id'], {
            'invoice_number': invoice.invoice_number, 'seller_name': data.get('seller_name',''),
            'seller_pin': data.get('seller_pin',''), 'buyer_name': data.get('buyer_name',''),
            'buyer_pin': data.get('buyer_pin',''), 'items': items,
            'subtotal': invoice.subtotal, 'vat': invoice.total_vat, 'total': invoice.grand_total,
            'invoice_type': data.get('invoice_type', 'standard'), 'date': invoice.date,
            'is_recurring': data.get('is_recurring', 'no') != 'no',
            'recurrence_interval': data.get('is_recurring', 'no')
        })

    return jsonify({
        "invoice_number": invoice.invoice_number, "date": invoice.date,
        "item_count": len(items), "subtotal": invoice.subtotal,
        "vat": invoice.total_vat, "total": invoice.grand_total,
        "download_text": invoice_text
    })

@app.route("/api/tax-return", methods=["POST"])
def api_tax_return():
    data = request.json
    return_type = data.get("return_type", "income_tax")
    ref = f"TR_{uuid.uuid4().hex[:10].upper()}"

    if return_type == "paye":
        employees = data.get("employees", [])
        total_paye = 0
        employee_details = []
        for emp in employees:
            result = calculate_paye(float(emp.get("gross", 0)))
            total_paye += result.tax_after_relief
            employee_details.append({
                "name": emp.get("name", ""), "pin": emp.get("pin", ""),
                "gross": result.gross_salary, "nssf": result.nssf, "nhif": result.nhif,
                "paye": result.tax_after_relief, "net": result.net_salary
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
                "Upload CSV or fill P10 form",
                "Submit and pay via M-Pesa Paybill 572572"
            ]
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
                "Enter output and input VAT",
                "Submit and pay via M-Pesa Paybill 572572"
            ]
        })

    elif return_type == "corporate":
        result = calculate_corporate_tax(
            float(data.get("gross_income", 0)),
            float(data.get("expenses", 0)),
            data.get("is_sme", False),
            float(data.get("installments", 0))
        )
        return jsonify({
            "status": "success", "ref": ref, "return_type": "Corporate Tax",
            "gross_income": result.gross_income,
            "allowable_expenses": result.allowable_expenses,
            "taxable_income": result.taxable_income,
            "tax_rate": result.tax_rate,
            "tax_payable": round(result.tax_payable, 2),
            "installments_paid": result.installments_paid,
            "balance_due": round(result.balance_due, 2),
            "filing_steps": [
                "Login to iTax at itax.kra.go.ke",
                "Go to Returns > File Return > Corporate Tax",
                "Enter income and expenses",
                "Submit and pay balance via M-Pesa Paybill 572572"
            ]
        })

    elif return_type == "turnover":
        result = calculate_turnover_tax(float(data.get("turnover", 0)))
        return jsonify({
            "status": "success", "ref": ref, "return_type": "Turnover Tax",
            "period": data.get("period", datetime.now().strftime("%B %Y")),
            "gross_turnover": result.gross_turnover,
            "tax_rate": result.tax_rate,
            "tax_payable": round(result.tax_payable, 2),
            "filing_steps": [
                "Login to iTax at itax.kra.go.ke",
                "Go to Returns > File Return > Turnover Tax",
                "Enter gross turnover for the period",
                "Submit and pay via M-Pesa Paybill 572572"
            ]
        })

    else:
        # Income Tax IT1
        gross_annual = float(data.get("annual_income", 0))
        monthly = gross_annual / 12
        result = calculate_paye(monthly)
        annual_tax = result.tax_after_relief * 12
        annual_nssf = result.nssf * 12
        other_income = float(data.get("other_income", 0))
        deductions = float(data.get("deductions", 0))
        withholding_tax = float(data.get("withholding_tax", 0))
        paye_paid = float(data.get("paye_already_paid", 0)) or annual_tax
        total_income = gross_annual + other_income
        taxable = total_income - annual_nssf - deductions
        monthly_taxable = taxable / 12
        recalc = calculate_paye(monthly_taxable + result.nssf)
        final_tax = recalc.tax_after_relief * 12
        tax_balance = final_tax - paye_paid - withholding_tax

        return jsonify({
            "status": "success", "ref": ref, "return_type": "Income Tax (IT1)",
            "tax_year": data.get("tax_year", str(datetime.now().year - 1)),
            "employment_income": gross_annual, "other_income": other_income,
            "total_income": total_income, "nssf_deduction": round(annual_nssf, 2),
            "other_deductions": deductions, "taxable_income": round(taxable, 2),
            "tax_charged": round(final_tax, 2), "personal_relief": 28800,
            "paye_already_paid": paye_paid, "withholding_tax": withholding_tax,
            "tax_balance": round(tax_balance, 2),
            "refund_or_payable": "REFUND" if tax_balance < 0 else "PAYABLE",
            "filing_steps": [
                "Login to iTax at itax.kra.go.ke",
                "Go to Returns > File Return > Income Tax Resident Individual",
                "Fill employment income, other income, deductions",
                "Review computed tax and submit",
                "Pay balance via M-Pesa Paybill 572572 or request refund"
            ]
        })

@app.route("/api/payroll", methods=["POST"])
def api_payroll():
    data = request.json
    result = process_payroll(data.get("employees", []))
    user = get_current_user()
    if user:
        save_payroll_run(user['id'], {
            'period': result['period'], 'employees': result['payslips'],
            'total_gross': result['totals']['total_gross'],
            'total_paye': result['totals']['paye'],
            'total_nssf': result['totals']['nssf'],
            'total_nhif': result['totals']['nhif'],
            'total_net': result['totals']['net']
        })
    return jsonify(result)

@app.route("/api/p9", methods=["POST"])
def api_p9():
    data = request.json
    monthly_gross = float(data.get("monthly_gross", 0))
    monthly_data = [{"gross": monthly_gross} for _ in range(12)]
    p9 = generate_p9_form(data.get("name", ""), data.get("kra_pin", ""), monthly_data)
    p9['download_text'] = generate_p9_text(p9)
    return jsonify(p9)

@app.route("/api/expenses", methods=["GET", "POST"])
def api_expenses():
    user = get_current_user()
    if request.method == "POST":
        data = request.json
        uid = user['id'] if user else 'anonymous'
        exp = save_expense(uid, data)
        return jsonify({"status": "success", "expense": exp})
    uid = user['id'] if user else 'anonymous'
    expenses = get_expenses(uid)
    summary = get_expense_summary(uid)
    return jsonify({"expenses": expenses, "summary": summary})

@app.route("/api/expenses/import", methods=["POST"])
def api_expenses_import():
    user = get_current_user()
    uid = user['id'] if user else 'anonymous'
    data = request.json
    expenses_list = data.get('expenses', [])
    if not expenses_list:
        return jsonify({"error": "No expenses to import"})
    saved = save_expenses_bulk(uid, expenses_list)
    return jsonify({"status": "success", "imported": len(saved)})


@app.route("/api/businesses", methods=["GET", "POST"])
def api_businesses():
    user = get_current_user()
    if not user:
        return jsonify({"businesses": []})
    if request.method == "POST":
        data = request.json
        biz = create_business(user['id'], data.get('name',''), data.get('kra_pin',''),
                             data.get('address',''), data.get('phone',''), data.get('email',''),
                             data.get('business_type','sole_proprietor'))
        return jsonify({"status": "success", "business": biz})
    return jsonify({"businesses": get_businesses(user['id'])})

@app.route("/api/reports/pnl", methods=["GET"])
def api_pnl():
    user = get_current_user()
    uid = user['id'] if user else 'anonymous'
    return jsonify(get_profit_loss(uid))

@app.route("/api/payment/initiate", methods=["POST"])
def api_payment_initiate():
    data = request.json
    result = initiate_mpesa_payment(data.get('phone',''), data.get('amount', 50), data.get('account_ref','KenyaComply'))
    user = get_current_user()
    if user and result.get('status') == 'success':
        save_payment(user['id'], {
            'tx_ref': result['data']['tx_ref'], 'phone': result['data']['phone'],
            'amount': data.get('amount', 50), 'status': 'pending',
            'description': data.get('account_ref', 'KenyaComply')
        })
    return jsonify(result)

@app.route("/api/payment/verify/<tx_ref>", methods=["GET"])
def api_payment_verify(tx_ref):
    result = verify_mpesa_payment(tx_ref)
    if result.get('status') == 'success':
        update_payment(tx_ref, {'status': 'completed', 'mpesa_receipt': result.get('data', {}).get('mpesa_receipt', '')})
    return jsonify(result)

@app.route("/api/mpesa/callback", methods=["POST"])
def api_mpesa_callback():
    result = process_mpesa_callback(request.json)
    return jsonify(result)

# ============================================
# AI TAX AGENT - Page & API
# ============================================
@app.route('/agent')
def agent_page():
    return render_template_string("""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Tax Agent - KenyaComply</title>
<style>""" + BASE_CSS + """
.agent-card { background:#fff; border-radius:12px; padding:20px; margin-bottom:16px; box-shadow:0 2px 8px rgba(0,0,0,0.08); }
.obligation { border-left:4px solid #007bff; padding:12px 16px; margin-bottom:10px; background:#f8f9fa; border-radius:0 8px 8px 0; }
.obligation.urgent { border-left-color:#dc3545; background:#fff5f5; }
.deadline-badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:13px; font-weight:600; }
.deadline-badge.urgent { background:#dc3545; color:#fff; }
.deadline-badge.normal { background:#28a745; color:#fff; }
.rec { padding:10px 14px; border-radius:8px; margin-bottom:8px; }
.rec.high { background:#fff3cd; border-left:4px solid #ffc107; }
.rec.medium { background:#d1ecf1; border-left:4px solid #17a2b8; }
.rec.info { background:#f0f0f0; border-left:4px solid #6c757d; }
.chat-box { border:1px solid #ddd; border-radius:12px; max-height:400px; overflow-y:auto; padding:16px; background:#fafafa; margin-bottom:12px; }
.chat-msg { margin-bottom:12px; padding:10px 14px; border-radius:10px; max-width:85%; }
.chat-msg.user { background:#007bff; color:#fff; margin-left:auto; }
.chat-msg.ai { background:#fff; border:1px solid #ddd; }
.chat-msg pre { white-space:pre-wrap; margin:8px 0 0; font-size:13px; }
.loading { text-align:center; padding:20px; color:#666; }
.summary-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-bottom:20px; }
.summary-item { background:#f8f9fa; padding:14px; border-radius:10px; text-align:center; }
.summary-item .val { font-size:22px; font-weight:700; color:#007bff; }
.summary-item .label { font-size:12px; color:#666; margin-top:4px; }
</style></head><body>
""" + NAVBAR_HTML + """
<div class="container">
<h1 style="margin-bottom:5px;">AI Tax Agent</h1>
<p style="color:#666; margin-bottom:20px;">Auto-analyzes your data, calculates obligations, prepares returns & answers tax questions</p>

<div class="tabs">
    <button class="tab active" onclick="showTab('agAnalysis',event)">Tax Analysis</button>
    <button class="tab" onclick="showTab('agPrepare',event)">Auto-Prepare Returns</button>
    <button class="tab" onclick="showTab('agAdvisor',event)">Tax Advisor Chat</button>
</div>

<!-- Tax Analysis -->
<div id="agAnalysis" class="tab-content">
    <div class="agent-card">
        <button class="btn btn-green btn-full" onclick="runAnalysis()" id="analyzeBtn">Analyze My Tax Obligations</button>
        <div id="analysisResult" class="loading hidden">Analyzing your data...</div>
    </div>
    <div id="analysisDash" class="hidden">
        <div id="summaryGrid" class="summary-grid"></div>
        <h3>Upcoming Deadlines</h3>
        <div id="deadlines"></div>
        <h3 style="margin-top:16px;">Tax Obligations</h3>
        <div id="obligations"></div>
        <h3 style="margin-top:16px;">Recommendations</h3>
        <div id="recommendations"></div>
    </div>
</div>

<!-- Auto-Prepare -->
<div id="agPrepare" class="tab-content hidden">
    <div class="agent-card">
        <h3>Auto-Prepare a Tax Return</h3>
        <p style="color:#666;margin-bottom:12px;">The agent fills in your return from invoices, expenses & payroll data.</p>
        <div class="form-group"><label>Return Type</label>
        <select id="prepReturnType">
            <option value="income_tax">Income Tax (IT1)</option>
            <option value="vat">VAT Return</option>
            <option value="paye">PAYE (P10)</option>
            <option value="corporate">Corporate Tax</option>
            <option value="turnover">Turnover Tax</option>
        </select></div>
        <button class="btn btn-blue btn-full" onclick="autoPrepare()">Auto-Prepare Return</button>
    </div>
    <div id="prepResult" class="hidden"></div>
</div>

<!-- Tax Advisor Chat -->
<div id="agAdvisor" class="tab-content hidden">
    <div class="agent-card">
        <h3>Ask the Tax Advisor</h3>
        <p style="color:#666;margin-bottom:12px;">AI-powered Kenyan tax advice. Ask about PAYE, VAT, deadlines, filing steps, penalties, and more.</p>
        <div class="chat-box" id="chatBox">
            <div class="chat-msg ai">Hello! I'm your KenyaComply Tax Advisor. Ask me anything about Kenyan taxes, KRA filing, deadlines, or compliance.</div>
        </div>
        <form onsubmit="askAdvisor(event)" style="display:flex;gap:8px;">
            <input type="text" id="chatInput" placeholder="e.g. When is PAYE due? How do I file nil returns?" style="flex:1;" required>
            <button type="submit" class="btn btn-green">Ask</button>
        </form>
    </div>
</div>
</div>

<script>
function showTab(id, e) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(id).classList.remove('hidden');
    if(e) e.target.classList.add('active');
}

async function runAnalysis() {
    const btn = document.getElementById('analyzeBtn');
    const loading = document.getElementById('analysisResult');
    btn.disabled = true; btn.textContent = 'Analyzing...';
    loading.classList.remove('hidden');
    try {
        const res = await fetch('/api/agent/analyze');
        const data = await res.json();
        if(data.error) { loading.innerHTML = '<div class="alert alert-danger">'+data.error+'</div>'; return; }
        document.getElementById('analysisDash').classList.remove('hidden');
        loading.classList.add('hidden');

        // Summary grid
        const s = data.summary;
        document.getElementById('summaryGrid').innerHTML =
            '<div class="summary-item"><div class="val">KES '+fmt(s.total_revenue)+'</div><div class="label">Total Revenue</div></div>'+
            '<div class="summary-item"><div class="val">KES '+fmt(s.total_expenses)+'</div><div class="label">Total Expenses</div></div>'+
            '<div class="summary-item"><div class="val">KES '+fmt(s.gross_profit)+'</div><div class="label">Gross Profit</div></div>'+
            '<div class="summary-item"><div class="val">KES '+fmt(data.total_tax_liability)+'</div><div class="label">Total Tax Liability</div></div>'+
            '<div class="summary-item"><div class="val">'+s.invoice_count+'</div><div class="label">Invoices</div></div>'+
            '<div class="summary-item"><div class="val">'+s.expense_count+'</div><div class="label">Expenses</div></div>';

        // Deadlines
        document.getElementById('deadlines').innerHTML = data.deadlines.map(d =>
            '<div class="obligation'+(d.urgent?' urgent':'')+'"><strong>'+d.label+'</strong> &mdash; '+d.deadline+
            ' <span class="deadline-badge '+(d.urgent?'urgent':'normal')+'">'+(d.days_left<=0?'OVERDUE':d.days_left+' days left')+'</span></div>'
        ).join('') || '<p style="color:#666;">No deadlines in the next 30 days.</p>';

        // Obligations
        document.getElementById('obligations').innerHTML = data.obligations.map(o =>
            '<div class="obligation"><strong>'+o.label+'</strong><br>Amount: <strong>KES '+fmt(o.amount)+'</strong><br>'+o.details+'<br><em>'+o.action+'</em></div>'
        ).join('') || '<p style="color:#666;">No obligations detected yet. Add invoices and expenses.</p>';

        // Recommendations
        document.getElementById('recommendations').innerHTML = data.recommendations.map(r =>
            '<div class="rec '+r.priority+'"><strong>'+r.message+'</strong><br><em>'+r.action+'</em></div>'
        ).join('');
    } catch(e) { loading.innerHTML = '<div class="alert alert-danger">Error: '+e.message+'</div>'; }
    finally { btn.disabled = false; btn.textContent = 'Analyze My Tax Obligations'; }
}

async function autoPrepare() {
    const type = document.getElementById('prepReturnType').value;
    const div = document.getElementById('prepResult');
    div.classList.remove('hidden');
    div.innerHTML = '<div class="loading">Preparing '+type+' return...</div>';
    try {
        const res = await fetch('/api/agent/prepare', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({return_type:type})});
        const data = await res.json();
        if(data.error) { div.innerHTML = '<div class="alert alert-danger">'+data.error+'</div>'; return; }
        let html = '<div class="agent-card"><h3>'+data.return_type.toUpperCase()+' Return (Auto-Filled)</h3>';
        html += '<p style="color:#666;">'+data.source+'</p>';
        if(data.instructions) html += '<div class="alert alert-info">'+data.instructions.map((s,i)=>(i+1)+'. '+s).join('<br>')+'</div>';
        html += '<table style="width:100%;margin-top:12px;">';
        for(const [k,v] of Object.entries(data.data||{})) {
            if(typeof v !== 'object') html += '<tr><td style="padding:6px 0;color:#666;">'+k.replace(/_/g,' ')+'</td><td style="padding:6px 0;font-weight:600;text-align:right;">'+(typeof v==='number'?'KES '+fmt(v):v)+'</td></tr>';
        }
        html += '</table>';
        if(data.csv_available) html += '<button class="btn btn-blue" style="margin-top:12px;" onclick="downloadCSV(\''+type+'\')">Download CSV for iTax</button>';
        html += '</div>';
        div.innerHTML = html;
    } catch(e) { div.innerHTML = '<div class="alert alert-danger">Error: '+e.message+'</div>'; }
}

async function downloadCSV(type) {
    const res = await fetch('/api/agent/csv?type='+type);
    const blob = await res.blob();
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
    a.download = 'kenyacomply_'+type+'_return.csv'; a.click();
}

async function askAdvisor(e) {
    e.preventDefault();
    const input = document.getElementById('chatInput');
    const q = input.value.trim(); if(!q) return;
    const box = document.getElementById('chatBox');
    box.innerHTML += '<div class="chat-msg user">'+q+'</div>';
    input.value = '';
    box.innerHTML += '<div class="chat-msg ai" id="typing" style="color:#999;">Thinking...</div>';
    box.scrollTop = box.scrollHeight;
    try {
        const res = await fetch('/api/agent/ask', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question:q})});
        const data = await res.json();
        document.getElementById('typing').remove();
        box.innerHTML += '<div class="chat-msg ai">'+(data.answer||'Sorry, I could not process that.').replace(/\\n/g,'<br>').replace(/\\*\\*(.*?)\\*\\*/g,'<strong>$1</strong>')+'</div>';
    } catch(err) {
        document.getElementById('typing').remove();
        box.innerHTML += '<div class="chat-msg ai" style="color:#dc3545;">Error: '+err.message+'</div>';
    }
    box.scrollTop = box.scrollHeight;
}

function fmt(n) { return Number(n||0).toLocaleString('en-KE',{minimumFractionDigits:0,maximumFractionDigits:0}); }
</script>
""" + FOOTER_HTML + "</body></html>")


@app.route("/api/agent/analyze")
def api_agent_analyze():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "Please log in to use the AI agent"})
    invoices = get_invoices(uid)
    expenses = get_expenses(uid)
    payroll_runs = get_payroll_runs(uid)
    employees = get_employees(uid)
    businesses = get_businesses(uid)
    result = analyze_user_data(invoices, expenses, payroll_runs, employees, businesses)
    return jsonify(result)


@app.route("/api/agent/prepare", methods=["POST"])
def api_agent_prepare():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "Please log in to use the AI agent"})
    data = request.json
    return_type = data.get("return_type", "income_tax")
    user_data = {
        'invoices': get_invoices(uid),
        'expenses': get_expenses(uid),
        'payroll_runs': get_payroll_runs(uid),
    }
    result = auto_prepare_return(return_type, user_data)
    if return_type in ('paye', 'vat'):
        result['csv_available'] = True
    return jsonify(result)


@app.route("/api/agent/csv")
def api_agent_csv():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "Please log in"})
    return_type = request.args.get('type', 'paye')
    user_data = {
        'invoices': get_invoices(uid),
        'expenses': get_expenses(uid),
        'payroll_runs': get_payroll_runs(uid),
    }
    prepared = auto_prepare_return(return_type, user_data)
    csv_data = generate_filing_csv(return_type, prepared.get('data', {}))
    from flask import Response
    return Response(csv_data, mimetype='text/csv',
                    headers={"Content-Disposition": f"attachment;filename=kenyacomply_{return_type}_return.csv"})


@app.route("/api/agent/ask", methods=["POST"])
def api_agent_ask():
    uid = session.get('user_id')
    context = None
    if uid:
        context = {
            'invoices': len(get_invoices(uid)),
            'expenses': len(get_expenses(uid)),
            'businesses': len(get_businesses(uid)),
        }
    question = request.json.get("question", "")
    if not question:
        return jsonify({"error": "Please provide a question"})
    result = ask_tax_advisor(question, context)
    return jsonify(result)


@app.route("/health")
def health():
    return {"status": "ok", "service": "kenya-comply", "version": "3.1", "db": "supabase" if not DB_DEMO_MODE else "in-memory"}

# Run the app
app.debug = True
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
