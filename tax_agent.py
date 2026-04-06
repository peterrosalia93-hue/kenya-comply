# KenyaComply - AI Tax Filing Agent
# Analyzes user data, auto-calculates obligations, prepares returns, guides filing

import os
import json
from datetime import datetime, timedelta
from tax_calculator import (
    calculate_paye, calculate_vat, calculate_corporate_tax,
    calculate_turnover_tax, calculate_withholding_tax
)

# Optional: Claude API for natural language tax advice
CLAUDE_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

try:
    import requests as http_requests
except ImportError:
    http_requests = None


# ============================================
# TAX DEADLINES
# ============================================
DEADLINES = {
    'income_tax': {'day': 30, 'month': 6, 'frequency': 'annual', 'label': 'Income Tax (IT1)'},
    'paye': {'day': 9, 'frequency': 'monthly', 'label': 'PAYE (P10)'},
    'vat': {'day': 20, 'frequency': 'monthly', 'label': 'VAT Return'},
    'corporate_tax': {'day': 30, 'month': 6, 'frequency': 'annual', 'label': 'Corporate Tax'},
    'turnover_tax': {'day': 20, 'frequency': 'monthly', 'label': 'Turnover Tax (TOT)'},
}

EXPENSE_CATEGORIES_DEDUCTIBLE = [
    'office', 'transport', 'utilities', 'rent', 'salaries',
    'marketing', 'professional', 'equipment', 'materials', 'insurance'
]


def get_upcoming_deadlines():
    """Get all upcoming tax deadlines in the next 30 days."""
    today = datetime.now()
    upcoming = []

    for tax_type, info in DEADLINES.items():
        if info['frequency'] == 'monthly':
            # Next deadline this month or next
            deadline_day = info['day']
            try:
                deadline = today.replace(day=deadline_day)
            except ValueError:
                deadline = today.replace(day=28)
            if deadline < today:
                if today.month == 12:
                    deadline = deadline.replace(year=today.year + 1, month=1)
                else:
                    deadline = deadline.replace(month=today.month + 1)

            days_left = (deadline - today).days
            if days_left <= 30:
                upcoming.append({
                    'type': tax_type,
                    'label': info['label'],
                    'deadline': deadline.strftime('%d %B %Y'),
                    'days_left': days_left,
                    'urgent': days_left <= 7
                })
        elif info['frequency'] == 'annual':
            deadline = today.replace(month=info['month'], day=info['day'])
            if deadline < today:
                deadline = deadline.replace(year=today.year + 1)
            days_left = (deadline - today).days
            if days_left <= 60:
                upcoming.append({
                    'type': tax_type,
                    'label': info['label'],
                    'deadline': deadline.strftime('%d %B %Y'),
                    'days_left': days_left,
                    'urgent': days_left <= 14
                })

    return sorted(upcoming, key=lambda x: x['days_left'])


def analyze_user_data(invoices, expenses, payroll_runs, employees, businesses):
    """
    Analyze all user data and determine tax obligations.
    Returns a comprehensive tax analysis with recommendations.
    """
    now = datetime.now()
    current_month = now.strftime('%B %Y')
    current_year = now.year

    # Revenue analysis
    total_revenue = sum(float(i.get('total', 0)) for i in invoices)
    total_subtotal = sum(float(i.get('subtotal', 0)) for i in invoices)
    total_vat_collected = sum(float(i.get('vat', 0)) for i in invoices)
    monthly_revenue = total_revenue / max(1, len(set(i.get('date', '')[:7] for i in invoices if i.get('date'))))

    # Expense analysis
    total_expenses = sum(float(e.get('amount', 0)) for e in expenses)
    total_input_vat = sum(float(e.get('vat_amount', 0)) for e in expenses)

    # Payroll analysis
    total_paye_liability = 0
    total_nssf = 0
    total_nhif = 0
    for run in payroll_runs:
        total_paye_liability += float(run.get('total_paye', 0))
        total_nssf += float(run.get('total_nssf', 0))
        total_nhif += float(run.get('total_nhif', 0))

    # Determine business type and applicable taxes
    annual_turnover_estimate = total_revenue * (12 / max(1, len(invoices)))
    is_vat_registered = annual_turnover_estimate > 5000000
    is_tot_eligible = annual_turnover_estimate < 25000000
    has_employees = len(employees) > 0 or len(payroll_runs) > 0
    is_company = any(b.get('business_type') == 'limited' for b in businesses)

    # Build obligations
    obligations = []

    # 1. Income Tax / Corporate Tax
    if is_company:
        taxable = total_subtotal - total_expenses
        corp_result = calculate_corporate_tax(total_subtotal, total_expenses, annual_turnover_estimate < 500000000)
        obligations.append({
            'type': 'corporate_tax',
            'label': 'Corporate Tax',
            'status': 'due',
            'amount': round(corp_result.tax_payable, 2),
            'details': f'Taxable income: KES {taxable:,.0f} at {corp_result.tax_rate}%',
            'action': 'File corporate tax return on iTax',
            'auto_data': {
                'gross_income': total_subtotal,
                'expenses': total_expenses,
                'taxable': taxable,
                'tax': round(corp_result.tax_payable, 2),
                'rate': corp_result.tax_rate
            }
        })
    else:
        # Individual income tax
        annual_income_estimate = total_subtotal
        monthly_est = annual_income_estimate / 12
        paye = calculate_paye(monthly_est)
        annual_tax = paye.tax_after_relief * 12
        obligations.append({
            'type': 'income_tax',
            'label': 'Income Tax (IT1)',
            'status': 'due',
            'amount': round(annual_tax, 2),
            'details': f'Estimated annual income: KES {annual_income_estimate:,.0f}',
            'action': 'File IT1 return on iTax by 30th June',
            'auto_data': {
                'annual_income': annual_income_estimate,
                'deductions': total_expenses,
                'estimated_tax': round(annual_tax, 2)
            }
        })

    # 2. VAT (if registered or should be)
    if is_vat_registered:
        net_vat = max(0, total_vat_collected - total_input_vat)
        obligations.append({
            'type': 'vat',
            'label': 'VAT Return',
            'status': 'due_monthly',
            'amount': round(net_vat, 2),
            'details': f'Output VAT: KES {total_vat_collected:,.0f} | Input VAT: KES {total_input_vat:,.0f}',
            'action': 'File monthly VAT return by 20th',
            'auto_data': {
                'output_sales': total_subtotal,
                'vat_collected': total_vat_collected,
                'input_vat': total_input_vat,
                'net_vat': round(net_vat, 2)
            }
        })
    elif annual_turnover_estimate > 4000000:
        obligations.append({
            'type': 'vat_warning',
            'label': 'VAT Registration Warning',
            'status': 'warning',
            'amount': 0,
            'details': f'Annual turnover ~KES {annual_turnover_estimate:,.0f} approaching KES 5M VAT threshold',
            'action': 'Register for VAT before crossing KES 5M threshold'
        })

    # 3. Turnover Tax (alternative to VAT for small businesses)
    if is_tot_eligible and not is_vat_registered:
        tot = calculate_turnover_tax(total_revenue)
        obligations.append({
            'type': 'turnover_tax',
            'label': 'Turnover Tax',
            'status': 'due_monthly',
            'amount': round(tot.tax_payable, 2),
            'details': f'3% of gross turnover KES {total_revenue:,.0f}',
            'action': 'File monthly TOT return by 20th',
            'auto_data': {
                'turnover': total_revenue,
                'tax': round(tot.tax_payable, 2)
            }
        })

    # 4. PAYE (if has employees)
    if has_employees:
        obligations.append({
            'type': 'paye',
            'label': 'PAYE (P10)',
            'status': 'due_monthly',
            'amount': round(total_paye_liability, 2),
            'details': f'{len(employees)} employees | Total PAYE: KES {total_paye_liability:,.0f}',
            'action': 'File monthly P10 by 9th',
            'auto_data': {
                'employee_count': len(employees),
                'total_paye': round(total_paye_liability, 2),
                'total_nssf': round(total_nssf, 2),
                'total_nhif': round(total_nhif, 2)
            }
        })

    # Recommendations
    recommendations = []

    if total_input_vat == 0 and total_expenses > 0:
        recommendations.append({
            'priority': 'high',
            'message': 'You have expenses but no input VAT recorded. Add VAT amounts to expenses to offset your VAT liability.',
            'action': 'Go to Expenses and update VAT amounts'
        })

    if not businesses:
        recommendations.append({
            'priority': 'medium',
            'message': 'Add your business details for better tax analysis and multi-business support.',
            'action': 'Go to My Businesses'
        })

    if has_employees and not payroll_runs:
        recommendations.append({
            'priority': 'high',
            'message': 'You have employees but no payroll runs. Process payroll to calculate PAYE obligations.',
            'action': 'Go to Payroll'
        })

    profit = total_subtotal - total_expenses
    if profit > 0:
        effective_rate = (obligations[0]['amount'] / profit * 100) if profit > 0 and obligations else 0
        recommendations.append({
            'priority': 'info',
            'message': f'Your effective tax rate is approximately {effective_rate:.1f}%. Gross profit: KES {profit:,.0f}',
            'action': 'Review Reports for detailed P&L'
        })

    deadlines = get_upcoming_deadlines()

    return {
        'summary': {
            'total_revenue': round(total_revenue, 2),
            'total_expenses': round(total_expenses, 2),
            'gross_profit': round(profit, 2),
            'annual_turnover_estimate': round(annual_turnover_estimate, 2),
            'is_vat_registered': is_vat_registered,
            'has_employees': has_employees,
            'is_company': is_company,
            'invoice_count': len(invoices),
            'expense_count': len(expenses),
        },
        'obligations': obligations,
        'deadlines': deadlines,
        'recommendations': recommendations,
        'total_tax_liability': round(sum(o['amount'] for o in obligations), 2)
    }


def auto_prepare_return(return_type, user_data):
    """
    Auto-prepare a tax return from user data.
    Returns pre-filled form data ready for filing.
    """
    invoices = user_data.get('invoices', [])
    expenses = user_data.get('expenses', [])
    payroll_runs = user_data.get('payroll_runs', [])

    if return_type == 'income_tax':
        total_income = sum(float(i.get('subtotal', 0)) for i in invoices)
        total_expenses_amount = sum(float(e.get('amount', 0)) for e in expenses)
        monthly = total_income / 12
        paye = calculate_paye(monthly)
        annual_tax = paye.tax_after_relief * 12
        annual_nssf = paye.nssf * 12

        return {
            'return_type': 'income_tax',
            'auto_filled': True,
            'data': {
                'annual_income': round(total_income, 2),
                'other_income': 0,
                'deductions': round(total_expenses_amount, 2),
                'nssf': round(annual_nssf, 2),
                'taxable_income': round(total_income - annual_nssf - total_expenses_amount, 2),
                'tax_charged': round(annual_tax, 2),
                'personal_relief': 28800,
                'paye_already_paid': 0,
                'withholding_tax': 0,
                'balance': round(annual_tax, 2)
            },
            'source': f'Auto-calculated from {len(invoices)} invoices and {len(expenses)} expenses',
            'instructions': [
                'Review the auto-filled figures below',
                'Adjust if you have additional income sources not in KenyaComply',
                'Add PAYE already deducted from P9 form if employed',
                'Click "File Return" to pay KES 100 and generate iTax-ready data'
            ]
        }

    elif return_type == 'vat':
        total_output = sum(float(i.get('subtotal', 0)) for i in invoices)
        total_vat_collected = sum(float(i.get('vat', 0)) for i in invoices)
        total_exempt = 0
        total_input_vat = sum(float(e.get('vat_amount', 0)) for e in expenses)

        return {
            'return_type': 'vat',
            'auto_filled': True,
            'data': {
                'output_sales': round(total_output, 2),
                'exempt_sales': 0,
                'vat_collected': round(total_vat_collected, 2),
                'input_vat': round(total_input_vat, 2),
                'net_vat': round(max(0, total_vat_collected - total_input_vat), 2)
            },
            'source': f'Auto-calculated from {len(invoices)} invoices and {len(expenses)} expenses',
            'instructions': [
                'Review output VAT from your sales invoices',
                'Verify input VAT from expense receipts',
                'Click "File Return" to generate iTax-ready data'
            ]
        }

    elif return_type == 'paye':
        # Get latest payroll data
        employees_data = []
        total_paye = 0
        for run in payroll_runs:
            emps = run.get('employees', '[]')
            if isinstance(emps, str):
                emps = json.loads(emps)
            for emp in emps:
                total_paye += float(emp.get('paye', 0))
                employees_data.append(emp)

        return {
            'return_type': 'paye',
            'auto_filled': True,
            'data': {
                'employees': employees_data,
                'total_paye': round(total_paye, 2),
                'employee_count': len(employees_data)
            },
            'source': f'Auto-calculated from {len(payroll_runs)} payroll runs',
            'instructions': [
                'Review employee PAYE deductions',
                'Verify against your payroll records',
                'Click "File Return" to generate P10 data for iTax'
            ]
        }

    elif return_type == 'corporate':
        total_income = sum(float(i.get('subtotal', 0)) for i in invoices)
        total_exp = sum(float(e.get('amount', 0)) for e in expenses)
        result = calculate_corporate_tax(total_income, total_exp)

        return {
            'return_type': 'corporate',
            'auto_filled': True,
            'data': {
                'gross_income': round(total_income, 2),
                'expenses': round(total_exp, 2),
                'taxable_income': round(result.taxable_income, 2),
                'tax_rate': result.tax_rate,
                'tax_payable': round(result.tax_payable, 2)
            },
            'source': f'Auto-calculated from {len(invoices)} invoices and {len(expenses)} expenses'
        }

    elif return_type == 'turnover':
        total_turnover = sum(float(i.get('total', 0)) for i in invoices)
        result = calculate_turnover_tax(total_turnover)

        return {
            'return_type': 'turnover',
            'auto_filled': True,
            'data': {
                'turnover': round(total_turnover, 2),
                'tax_rate': result.tax_rate,
                'tax_payable': round(result.tax_payable, 2)
            },
            'source': f'Auto-calculated from {len(invoices)} invoices'
        }

    return {'error': 'Unknown return type'}


def generate_filing_csv(return_type, return_data):
    """Generate CSV data for iTax upload."""
    if return_type == 'paye':
        lines = ['Employee Name,KRA PIN,Gross Pay,NSSF,Taxable Pay,PAYE,NHIF,Net Pay']
        for emp in return_data.get('employees', []):
            lines.append(
                f"{emp.get('name','')},{emp.get('kra_pin','')},{emp.get('gross_salary',0)},"
                f"{emp.get('nssf',0)},{emp.get('taxable_income',0)},{emp.get('paye',0)},"
                f"{emp.get('nhif',0)},{emp.get('net_salary',0)}"
            )
        return '\n'.join(lines)

    elif return_type == 'vat':
        lines = ['Field,Amount (KES)']
        data = return_data.get('data', {})
        lines.append(f"Output Sales,{data.get('output_sales',0)}")
        lines.append(f"Exempt Sales,{data.get('exempt_sales',0)}")
        lines.append(f"VAT Collected,{data.get('vat_collected',0)}")
        lines.append(f"Input VAT,{data.get('input_vat',0)}")
        lines.append(f"Net VAT Payable,{data.get('net_vat',0)}")
        return '\n'.join(lines)

    return ''


# ============================================
# AI TAX ADVISOR (Claude API)
# ============================================
SYSTEM_PROMPT = """You are KenyaComply Tax Advisor, an AI assistant specializing in Kenyan tax law and KRA compliance.

You help users with:
- Understanding their tax obligations (PAYE, VAT, Income Tax, Corporate Tax, Turnover Tax, Withholding Tax)
- Filing returns on iTax (itax.kra.go.ke)
- Tax planning and optimization (legally)
- Understanding KRA penalties and how to avoid them
- NSSF, NHIF, and housing levy questions
- Business registration and compliance

Key facts:
- PAYE bands: 10%-35% (2024 rates), personal relief KES 2,400/month
- VAT: 16% standard rate, threshold KES 5M annual turnover
- Corporate tax: 30% (25% for SMEs under KES 500M turnover)
- Turnover tax: 3% for businesses under KES 25M
- NSSF: 6% capped at KES 2,160/month
- Income tax deadline: 30th June
- PAYE deadline: 9th of next month
- VAT deadline: 20th of next month
- KRA Paybill: 572572

Always provide specific, actionable advice. Reference iTax steps when relevant.
Be concise but thorough. If unsure about a specific regulation, say so.
"""


def ask_tax_advisor(question, user_context=None):
    """
    Ask the AI tax advisor a question.
    Uses Claude API if available, otherwise falls back to rule-based answers.
    """
    # Try Claude API first
    if CLAUDE_API_KEY and http_requests:
        try:
            messages = [{"role": "user", "content": question}]
            if user_context:
                context = f"User context: {json.dumps(user_context)}\n\nQuestion: {question}"
                messages = [{"role": "user", "content": context}]

            resp = http_requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": CLAUDE_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1024,
                    "system": SYSTEM_PROMPT,
                    "messages": messages
                },
                timeout=30
            )

            if resp.status_code == 200:
                result = resp.json()
                text = result.get("content", [{}])[0].get("text", "")
                if text:
                    return {"status": "success", "answer": text, "source": "ai"}
        except Exception as e:
            pass  # Fall through to rule-based

    # Rule-based fallback
    return rule_based_answer(question)


def rule_based_answer(question):
    """Rule-based tax Q&A fallback when Claude API is not available."""
    q = question.lower()

    answers = {
        'paye': {
            'keywords': ['paye', 'pay as you earn', 'salary tax', 'employment tax'],
            'answer': """**PAYE (Pay As You Earn)**

PAYE is tax deducted from employment income. 2024 rates:
- First KES 24,000/month: 10%
- KES 24,001 - 32,000: 15%
- KES 32,001 - 40,000: 20%
- KES 40,001 - 50,000: 25%
- KES 50,001 - 80,000: 30%
- Above KES 80,000: 35%

Personal relief: KES 2,400/month deducted from tax.
NSSF (6%, max KES 2,160) is deducted before calculating tax.

**Filing:** Employers file P10 by 9th of next month on iTax.
**Payment:** Paybill 572572, Account: KRA PIN + PAYE"""
        },
        'vat': {
            'keywords': ['vat', 'value added tax', '16%'],
            'answer': """**VAT (Value Added Tax)**

- Standard rate: 16%
- Registration threshold: KES 5M annual turnover
- Filing deadline: 20th of the following month
- You can offset input VAT (on purchases) against output VAT (on sales)

**To file:** iTax > Returns > File Return > VAT
**Payment:** Paybill 572572, Account: KRA PIN + VAT

Keep all ETIMS invoices for 5 years as KRA can audit."""
        },
        'income': {
            'keywords': ['income tax', 'individual tax', 'it1', 'annual return', 'file return'],
            'answer': """**Income Tax Return (IT1)**

All individuals with a KRA PIN must file by **30th June** annually.

**What you need:**
- P9 form from employer
- Bank interest certificates
- Rental income records
- Business income records

**Steps on iTax:**
1. Login at itax.kra.go.ke
2. Returns > File Return > Income Tax Resident Individual
3. Fill employment income, other income, deductions
4. System auto-calculates tax and personal relief (KES 28,800/year)
5. Submit and pay any balance

**Penalty for late filing:** KES 20,000 or 5% of tax due (whichever is higher)"""
        },
        'corporate': {
            'keywords': ['corporate tax', 'company tax', 'limited company'],
            'answer': """**Corporate Tax**

- Standard rate: 30%
- SME rate (turnover < KES 500M): 25%
- Filing deadline: 6 months after financial year-end
- Installment tax due in 4 installments during the year

Allowable deductions include business expenses, depreciation, and bad debts."""
        },
        'turnover': {
            'keywords': ['turnover tax', 'tot', 'small business tax'],
            'answer': """**Turnover Tax (TOT)**

- Rate: 3% of gross turnover
- For businesses with annual turnover below KES 25M
- Alternative to income tax + VAT for small businesses
- Filed monthly by 20th of following month
- Simple: just declare gross sales and pay 3%

**Payment:** Paybill 572572, Account: KRA PIN + TOT"""
        },
        'deadline': {
            'keywords': ['deadline', 'when', 'due date', 'late', 'penalty'],
            'answer': """**Tax Deadlines & Penalties**

| Tax | Deadline | Late Penalty |
|-----|----------|-------------|
| Income Tax | 30th June | KES 20,000 or 5% |
| PAYE | 9th next month | 25% of PAYE + 5%/month |
| VAT | 20th next month | KES 10,000 + 5% |
| Corporate Tax | 6mo after year-end | 5% + 1%/month |
| Turnover Tax | 20th next month | KES 1,000/month |

**Tip:** File nil returns even with zero income to avoid penalties."""
        },
        'mpesa': {
            'keywords': ['mpesa', 'm-pesa', 'pay kra', 'paybill', '572572'],
            'answer': """**Pay KRA via M-Pesa**

1. Go to M-Pesa > Lipa na M-Pesa > Pay Bill
2. Business Number: **572572**
3. Account Number: Your KRA PIN + Tax Code

| Tax | Account Format |
|-----|---------------|
| Income Tax | PIN + IT |
| PAYE | PIN + PAYE |
| VAT | PIN + VAT |
| Corporate Tax | PIN + CT |

Example: A123456789BIT for income tax."""
        },
        'nil': {
            'keywords': ['nil return', 'no income', 'zero return'],
            'answer': """**Nil Returns**

Even with NO income, you must file a nil return to avoid the KES 20,000 penalty.

**How to file:**
1. Login to iTax
2. Returns > File Return > Income Tax
3. Select "Nil Return"
4. Submit — no payment needed

You should also file nil PAYE if you're registered as an employer but had no employees that month."""
        },
        'kra_pin': {
            'keywords': ['kra pin', 'register', 'get pin', 'new pin'],
            'answer': """**Getting a KRA PIN**

1. Go to itax.kra.go.ke
2. Click "New PIN Registration"
3. Choose: Individual, Company, or Partnership
4. Fill in personal/company details
5. Upload ID/passport copy
6. Submit — PIN is generated immediately

You need: National ID or passport, email address, phone number."""
        }
    }

    # Find best matching answer
    best_match = None
    best_score = 0
    for key, data in answers.items():
        score = sum(1 for kw in data['keywords'] if kw in q)
        if score > best_score:
            best_score = score
            best_match = data['answer']

    if best_match:
        return {"status": "success", "answer": best_match, "source": "knowledge_base"}

    # Default answer
    return {
        "status": "success",
        "source": "knowledge_base",
        "answer": """I can help with Kenyan tax questions. Try asking about:

- **PAYE** — salary tax rates and filing
- **VAT** — value added tax obligations
- **Income Tax** — annual return filing (IT1)
- **Corporate Tax** — company tax rates
- **Turnover Tax** — for small businesses
- **Deadlines** — when each tax is due
- **M-Pesa payments** — how to pay KRA
- **Nil returns** — filing with zero income
- **KRA PIN** — how to register

Or ask any specific tax question and I'll help!"""
    }
