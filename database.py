# KenyaComply - Supabase Database Layer
# Persistent storage for users, invoices, payments, tax returns, expenses

import os
import json
import uuid
from datetime import datetime

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')

# In-memory fallback when Supabase is not configured
DEMO_MODE = not (SUPABASE_URL and SUPABASE_KEY and create_client)

_supabase = None

def get_db():
    """Get Supabase client (cached)."""
    global _supabase
    if DEMO_MODE:
        return None
    if _supabase is None:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase

# ============================================
# IN-MEMORY FALLBACK STORES
# ============================================
_mem = {
    'users': {},
    'invoices': {},
    'payments': {},
    'tax_returns': {},
    'expenses': {},
    'employees': {},
    'businesses': {},
    'reminders': {}
}

def _gen_id():
    return str(uuid.uuid4())

def _now():
    return datetime.now().isoformat()

# ============================================
# USERS
# ============================================
def create_user(email, name, password_hash='', kra_pin='', phone=''):
    uid = _gen_id()
    user = {
        'id': uid, 'email': email, 'name': name, 'password_hash': password_hash,
        'kra_pin': kra_pin, 'phone': phone, 'plan': 'free',
        'created_at': _now(), 'updated_at': _now()
    }
    db = get_db()
    if db:
        result = db.table('users').insert(user).execute()
        return result.data[0] if result.data else user
    _mem['users'][uid] = user
    return user

def get_user_by_email(email):
    db = get_db()
    if db:
        result = db.table('users').select('*').eq('email', email).execute()
        return result.data[0] if result.data else None
    for u in _mem['users'].values():
        if u['email'] == email:
            return u
    return None

def get_user_by_id(uid):
    db = get_db()
    if db:
        result = db.table('users').select('*').eq('id', uid).execute()
        return result.data[0] if result.data else None
    return _mem['users'].get(uid)

def update_user(uid, updates):
    updates['updated_at'] = _now()
    db = get_db()
    if db:
        result = db.table('users').update(updates).eq('id', uid).execute()
        return result.data[0] if result.data else None
    if uid in _mem['users']:
        _mem['users'][uid].update(updates)
        return _mem['users'][uid]
    return None

# ============================================
# BUSINESSES (multi-business support)
# ============================================
def create_business(user_id, name, kra_pin, address='', phone='', email='', business_type='sole_proprietor'):
    bid = _gen_id()
    biz = {
        'id': bid, 'user_id': user_id, 'name': name, 'kra_pin': kra_pin,
        'address': address, 'phone': phone, 'email': email,
        'business_type': business_type, 'vat_registered': False,
        'created_at': _now()
    }
    db = get_db()
    if db:
        result = db.table('businesses').insert(biz).execute()
        return result.data[0] if result.data else biz
    _mem['businesses'][bid] = biz
    return biz

def get_businesses(user_id):
    db = get_db()
    if db:
        result = db.table('businesses').select('*').eq('user_id', user_id).execute()
        return result.data or []
    return [b for b in _mem['businesses'].values() if b['user_id'] == user_id]

# ============================================
# INVOICES
# ============================================
def save_invoice(user_id, invoice_data):
    iid = invoice_data.get('id', _gen_id())
    invoice = {
        'id': iid, 'user_id': user_id,
        'invoice_number': invoice_data.get('invoice_number', ''),
        'seller_name': invoice_data.get('seller_name', ''),
        'seller_pin': invoice_data.get('seller_pin', ''),
        'buyer_name': invoice_data.get('buyer_name', ''),
        'buyer_pin': invoice_data.get('buyer_pin', ''),
        'items': json.dumps(invoice_data.get('items', [])),
        'subtotal': invoice_data.get('subtotal', 0),
        'vat': invoice_data.get('vat', 0),
        'total': invoice_data.get('total', 0),
        'status': invoice_data.get('status', 'draft'),
        'invoice_type': invoice_data.get('invoice_type', 'standard'),
        'is_recurring': invoice_data.get('is_recurring', False),
        'recurrence_interval': invoice_data.get('recurrence_interval', ''),
        'date': invoice_data.get('date', _now()),
        'created_at': _now()
    }
    db = get_db()
    if db:
        result = db.table('invoices').insert(invoice).execute()
        return result.data[0] if result.data else invoice
    _mem['invoices'][iid] = invoice
    return invoice

def get_invoices(user_id, limit=50):
    db = get_db()
    if db:
        result = db.table('invoices').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(limit).execute()
        return result.data or []
    invs = [i for i in _mem['invoices'].values() if i['user_id'] == user_id]
    return sorted(invs, key=lambda x: x['created_at'], reverse=True)[:limit]

def get_invoice(invoice_id):
    db = get_db()
    if db:
        result = db.table('invoices').select('*').eq('id', invoice_id).execute()
        return result.data[0] if result.data else None
    return _mem['invoices'].get(invoice_id)

# ============================================
# PAYMENTS
# ============================================
def save_payment(user_id, payment_data):
    pid = payment_data.get('id', _gen_id())
    payment = {
        'id': pid, 'user_id': user_id,
        'tx_ref': payment_data.get('tx_ref', ''),
        'phone': payment_data.get('phone', ''),
        'amount': payment_data.get('amount', 0),
        'status': payment_data.get('status', 'pending'),
        'mpesa_receipt': payment_data.get('mpesa_receipt', ''),
        'checkout_request_id': payment_data.get('checkout_request_id', ''),
        'description': payment_data.get('description', ''),
        'created_at': _now()
    }
    db = get_db()
    if db:
        result = db.table('payments').insert(payment).execute()
        return result.data[0] if result.data else payment
    _mem['payments'][pid] = payment
    return payment

def get_payments(user_id, limit=50):
    db = get_db()
    if db:
        result = db.table('payments').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(limit).execute()
        return result.data or []
    pays = [p for p in _mem['payments'].values() if p['user_id'] == user_id]
    return sorted(pays, key=lambda x: x['created_at'], reverse=True)[:limit]

def update_payment(tx_ref, updates):
    db = get_db()
    if db:
        result = db.table('payments').update(updates).eq('tx_ref', tx_ref).execute()
        return result.data[0] if result.data else None
    for p in _mem['payments'].values():
        if p['tx_ref'] == tx_ref:
            p.update(updates)
            return p
    return None

# ============================================
# TAX RETURNS
# ============================================
def save_tax_return(user_id, return_data):
    rid = return_data.get('id', _gen_id())
    tr = {
        'id': rid, 'user_id': user_id,
        'ref': return_data.get('ref', ''),
        'return_type': return_data.get('return_type', ''),
        'period': return_data.get('period', ''),
        'data': json.dumps(return_data.get('data', {})),
        'total_tax': return_data.get('total_tax', 0),
        'status': return_data.get('status', 'calculated'),
        'payment_ref': return_data.get('payment_ref', ''),
        'created_at': _now()
    }
    db = get_db()
    if db:
        result = db.table('tax_returns').insert(tr).execute()
        return result.data[0] if result.data else tr
    _mem['tax_returns'][rid] = tr
    return tr

def get_tax_returns(user_id, limit=50):
    db = get_db()
    if db:
        result = db.table('tax_returns').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(limit).execute()
        return result.data or []
    trs = [t for t in _mem['tax_returns'].values() if t['user_id'] == user_id]
    return sorted(trs, key=lambda x: x['created_at'], reverse=True)[:limit]

# ============================================
# EXPENSES
# ============================================
def save_expense(user_id, expense_data):
    eid = expense_data.get('id', _gen_id())
    exp = {
        'id': eid, 'user_id': user_id,
        'business_id': expense_data.get('business_id', ''),
        'description': expense_data.get('description', ''),
        'category': expense_data.get('category', 'general'),
        'amount': expense_data.get('amount', 0),
        'vat_amount': expense_data.get('vat_amount', 0),
        'supplier': expense_data.get('supplier', ''),
        'supplier_pin': expense_data.get('supplier_pin', ''),
        'receipt_ref': expense_data.get('receipt_ref', ''),
        'payment_method': expense_data.get('payment_method', 'cash'),
        'card_last4': expense_data.get('card_last4', ''),
        'card_bank': expense_data.get('card_bank', ''),
        'mpesa_ref': expense_data.get('mpesa_ref', ''),
        'import_source': expense_data.get('import_source', 'manual'),
        'date': expense_data.get('date', _now()[:10]),
        'created_at': _now()
    }
    db = get_db()
    if db:
        result = db.table('expenses').insert(exp).execute()
        return result.data[0] if result.data else exp
    _mem['expenses'][eid] = exp
    return exp

def get_expenses(user_id, business_id=None, limit=100):
    db = get_db()
    if db:
        q = db.table('expenses').select('*').eq('user_id', user_id)
        if business_id:
            q = q.eq('business_id', business_id)
        result = q.order('date', desc=True).limit(limit).execute()
        return result.data or []
    exps = [e for e in _mem['expenses'].values() if e['user_id'] == user_id]
    if business_id:
        exps = [e for e in exps if e.get('business_id') == business_id]
    return sorted(exps, key=lambda x: x.get('date', ''), reverse=True)[:limit]

def get_expense_summary(user_id, business_id=None):
    expenses = get_expenses(user_id, business_id, limit=1000)
    total = sum(e.get('amount', 0) for e in expenses)
    total_vat = sum(e.get('vat_amount', 0) for e in expenses)
    by_category = {}
    for e in expenses:
        cat = e.get('category', 'general')
        by_category[cat] = by_category.get(cat, 0) + e.get('amount', 0)
    return {'total': total, 'total_vat': total_vat, 'by_category': by_category, 'count': len(expenses)}

def save_expenses_bulk(user_id, expenses_list):
    """Save multiple expenses at once (for CSV/M-Pesa import)."""
    saved = []
    for exp_data in expenses_list:
        saved.append(save_expense(user_id, exp_data))
    return saved


# ============================================
# EMPLOYEES (Payroll)
# ============================================
def save_employee(user_id, employee_data):
    eid = employee_data.get('id', _gen_id())
    emp = {
        'id': eid, 'user_id': user_id,
        'business_id': employee_data.get('business_id', ''),
        'name': employee_data.get('name', ''),
        'kra_pin': employee_data.get('kra_pin', ''),
        'id_number': employee_data.get('id_number', ''),
        'phone': employee_data.get('phone', ''),
        'email': employee_data.get('email', ''),
        'gross_salary': employee_data.get('gross_salary', 0),
        'allowances': employee_data.get('allowances', 0),
        'status': employee_data.get('status', 'active'),
        'start_date': employee_data.get('start_date', _now()[:10]),
        'created_at': _now()
    }
    db = get_db()
    if db:
        result = db.table('employees').insert(emp).execute()
        return result.data[0] if result.data else emp
    _mem['employees'][eid] = emp
    return emp

def get_employees(user_id, business_id=None, status='active'):
    db = get_db()
    if db:
        q = db.table('employees').select('*').eq('user_id', user_id).eq('status', status)
        if business_id:
            q = q.eq('business_id', business_id)
        result = q.order('name').execute()
        return result.data or []
    emps = [e for e in _mem['employees'].values() if e['user_id'] == user_id and e.get('status') == status]
    if business_id:
        emps = [e for e in emps if e.get('business_id') == business_id]
    return sorted(emps, key=lambda x: x.get('name', ''))

def update_employee(eid, updates):
    db = get_db()
    if db:
        result = db.table('employees').update(updates).eq('id', eid).execute()
        return result.data[0] if result.data else None
    if eid in _mem['employees']:
        _mem['employees'][eid].update(updates)
        return _mem['employees'][eid]
    return None

def delete_employee(eid):
    return update_employee(eid, {'status': 'inactive'})

# ============================================
# PAYROLL RUNS
# ============================================
def save_payroll_run(user_id, payroll_data):
    pid = _gen_id()
    pr = {
        'id': pid, 'user_id': user_id,
        'business_id': payroll_data.get('business_id', ''),
        'period': payroll_data.get('period', ''),
        'employees': json.dumps(payroll_data.get('employees', [])),
        'total_gross': payroll_data.get('total_gross', 0),
        'total_paye': payroll_data.get('total_paye', 0),
        'total_nssf': payroll_data.get('total_nssf', 0),
        'total_nhif': payroll_data.get('total_nhif', 0),
        'total_net': payroll_data.get('total_net', 0),
        'status': payroll_data.get('status', 'processed'),
        'created_at': _now()
    }
    db = get_db()
    if db:
        result = db.table('payroll_runs').insert(pr).execute()
        return result.data[0] if result.data else pr
    _mem.setdefault('payroll_runs', {})[pid] = pr
    return pr

def get_payroll_runs(user_id, limit=20):
    db = get_db()
    if db:
        result = db.table('payroll_runs').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(limit).execute()
        return result.data or []
    runs = [r for r in _mem.get('payroll_runs', {}).values() if r['user_id'] == user_id]
    return sorted(runs, key=lambda x: x['created_at'], reverse=True)[:limit]

# ============================================
# P&L / REPORTS
# ============================================
def get_profit_loss(user_id, business_id=None):
    """Generate P&L from invoices (revenue) and expenses."""
    invoices = get_invoices(user_id, limit=1000)
    expenses = get_expenses(user_id, business_id, limit=1000)

    total_revenue = sum(float(i.get('subtotal', 0)) for i in invoices)
    total_vat_collected = sum(float(i.get('vat', 0)) for i in invoices)
    total_expenses = sum(float(e.get('amount', 0)) for e in expenses)
    total_input_vat = sum(float(e.get('vat_amount', 0)) for e in expenses)

    expense_by_cat = {}
    for e in expenses:
        cat = e.get('category', 'general')
        expense_by_cat[cat] = expense_by_cat.get(cat, 0) + float(e.get('amount', 0))

    gross_profit = total_revenue - total_expenses
    net_vat = total_vat_collected - total_input_vat

    return {
        'total_revenue': round(total_revenue, 2),
        'total_vat_collected': round(total_vat_collected, 2),
        'total_expenses': round(total_expenses, 2),
        'total_input_vat': round(total_input_vat, 2),
        'expense_by_category': expense_by_cat,
        'gross_profit': round(gross_profit, 2),
        'net_vat_payable': round(max(0, net_vat), 2),
        'invoice_count': len(invoices),
        'expense_count': len(expenses)
    }

# ============================================
# SUPABASE SCHEMA (run once)
# ============================================
SCHEMA_SQL = """
-- Users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT DEFAULT '',
    kra_pin TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    plan TEXT DEFAULT 'free',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Businesses
CREATE TABLE IF NOT EXISTS businesses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name TEXT NOT NULL,
    kra_pin TEXT NOT NULL,
    address TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    email TEXT DEFAULT '',
    business_type TEXT DEFAULT 'sole_proprietor',
    vat_registered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Invoices
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    invoice_number TEXT NOT NULL,
    seller_name TEXT, seller_pin TEXT,
    buyer_name TEXT, buyer_pin TEXT,
    items JSONB DEFAULT '[]',
    subtotal NUMERIC DEFAULT 0,
    vat NUMERIC DEFAULT 0,
    total NUMERIC DEFAULT 0,
    status TEXT DEFAULT 'draft',
    invoice_type TEXT DEFAULT 'standard',
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence_interval TEXT DEFAULT '',
    date TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Payments
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    tx_ref TEXT, phone TEXT,
    amount NUMERIC DEFAULT 0,
    status TEXT DEFAULT 'pending',
    mpesa_receipt TEXT DEFAULT '',
    checkout_request_id TEXT DEFAULT '',
    description TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tax Returns
CREATE TABLE IF NOT EXISTS tax_returns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    ref TEXT, return_type TEXT, period TEXT,
    data JSONB DEFAULT '{}',
    total_tax NUMERIC DEFAULT 0,
    status TEXT DEFAULT 'calculated',
    payment_ref TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Expenses
CREATE TABLE IF NOT EXISTS expenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    business_id TEXT DEFAULT '',
    description TEXT, category TEXT DEFAULT 'general',
    amount NUMERIC DEFAULT 0,
    vat_amount NUMERIC DEFAULT 0,
    supplier TEXT DEFAULT '', supplier_pin TEXT DEFAULT '',
    receipt_ref TEXT DEFAULT '',
    date TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Employees
CREATE TABLE IF NOT EXISTS employees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    business_id TEXT DEFAULT '',
    name TEXT NOT NULL, kra_pin TEXT DEFAULT '',
    id_number TEXT DEFAULT '', phone TEXT DEFAULT '', email TEXT DEFAULT '',
    gross_salary NUMERIC DEFAULT 0,
    allowances NUMERIC DEFAULT 0,
    status TEXT DEFAULT 'active',
    start_date TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Payroll Runs
CREATE TABLE IF NOT EXISTS payroll_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    business_id TEXT DEFAULT '',
    period TEXT,
    employees JSONB DEFAULT '[]',
    total_gross NUMERIC DEFAULT 0,
    total_paye NUMERIC DEFAULT 0,
    total_nssf NUMERIC DEFAULT 0,
    total_nhif NUMERIC DEFAULT 0,
    total_net NUMERIC DEFAULT 0,
    status TEXT DEFAULT 'processed',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_invoices_user ON invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_txref ON payments(tx_ref);
CREATE INDEX IF NOT EXISTS idx_expenses_user ON expenses(user_id);
CREATE INDEX IF NOT EXISTS idx_employees_user ON employees(user_id);
CREATE INDEX IF NOT EXISTS idx_tax_returns_user ON tax_returns(user_id);
"""
