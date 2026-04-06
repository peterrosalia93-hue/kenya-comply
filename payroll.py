# KenyaComply - Payroll Module
# Monthly salary processing with auto PAYE, NSSF, NHIF calculations
# P9 form generation for employees

from datetime import datetime
from tax_calculator import calculate_paye, calculate_nhif

def process_payroll(employees):
    """
    Process monthly payroll for a list of employees.

    Args:
        employees: list of dicts with keys: name, kra_pin, gross_salary, allowances

    Returns:
        dict with payslips and totals
    """
    payslips = []
    totals = {
        'gross': 0, 'allowances': 0, 'total_gross': 0,
        'nssf': 0, 'nhif': 0, 'paye': 0, 'net': 0
    }

    for emp in employees:
        gross = float(emp.get('gross_salary', 0))
        allowances = float(emp.get('allowances', 0))
        total_gross = gross + allowances

        result = calculate_paye(total_gross)

        payslip = {
            'name': emp.get('name', ''),
            'kra_pin': emp.get('kra_pin', ''),
            'id_number': emp.get('id_number', ''),
            'basic_salary': gross,
            'allowances': allowances,
            'gross_salary': total_gross,
            'nssf': result.nssf,
            'taxable_income': result.taxable_income,
            'tax_before_relief': result.tax_before_relief,
            'personal_relief': result.personal_relief,
            'paye': result.tax_after_relief,
            'nhif': result.nhif,
            'total_deductions': result.nssf + result.tax_after_relief + result.nhif,
            'net_salary': result.net_salary
        }
        payslips.append(payslip)

        totals['gross'] += gross
        totals['allowances'] += allowances
        totals['total_gross'] += total_gross
        totals['nssf'] += result.nssf
        totals['nhif'] += result.nhif
        totals['paye'] += result.tax_after_relief
        totals['net'] += result.net_salary

    # Round totals
    for k in totals:
        totals[k] = round(totals[k], 2)

    return {
        'period': datetime.now().strftime('%B %Y'),
        'payslips': payslips,
        'totals': totals,
        'employee_count': len(payslips)
    }


def generate_p9_form(employee_name, kra_pin, monthly_data):
    """
    Generate P9 form data for annual tax filing.

    Args:
        employee_name: Employee full name
        kra_pin: Employee KRA PIN
        monthly_data: list of 12 dicts with monthly payroll data
            Each: {gross, paye, nssf, nhif, personal_relief}

    Returns:
        dict with P9 form fields
    """
    annual = {
        'gross': 0, 'nssf': 0, 'taxable': 0,
        'tax_charged': 0, 'personal_relief': 0,
        'paye': 0, 'nhif': 0
    }

    months = []
    month_names = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]

    for i, m in enumerate(monthly_data):
        gross = float(m.get('gross', 0))
        result = calculate_paye(gross)

        month_entry = {
            'month': month_names[i] if i < 12 else f'Month {i+1}',
            'gross': gross,
            'nssf': result.nssf,
            'taxable': result.taxable_income,
            'tax_charged': result.tax_before_relief,
            'personal_relief': result.personal_relief,
            'paye': result.tax_after_relief,
            'nhif': result.nhif
        }
        months.append(month_entry)

        annual['gross'] += gross
        annual['nssf'] += result.nssf
        annual['taxable'] += result.taxable_income
        annual['tax_charged'] += result.tax_before_relief
        annual['personal_relief'] += result.personal_relief
        annual['paye'] += result.tax_after_relief
        annual['nhif'] += result.nhif

    for k in annual:
        annual[k] = round(annual[k], 2)

    return {
        'employee_name': employee_name,
        'kra_pin': kra_pin,
        'tax_year': datetime.now().year,
        'employer': 'As per employer records',
        'months': months,
        'annual_totals': annual,
        'form_type': 'P9',
        'generated_at': datetime.now().isoformat()
    }


def generate_p9_text(p9_data):
    """Generate downloadable P9 form as text."""
    lines = []
    lines.append("=" * 70)
    lines.append("KRA P9 TAX DEDUCTION CARD")
    lines.append(f"Tax Year: {p9_data['tax_year']}")
    lines.append("=" * 70)
    lines.append(f"Employee: {p9_data['employee_name']}")
    lines.append(f"KRA PIN:  {p9_data['kra_pin']}")
    lines.append("-" * 70)
    lines.append(f"{'Month':<12} {'Gross':>10} {'NSSF':>8} {'Taxable':>10} {'Tax':>10} {'Relief':>8} {'PAYE':>10}")
    lines.append("-" * 70)

    for m in p9_data['months']:
        lines.append(
            f"{m['month']:<12} {m['gross']:>10,.0f} {m['nssf']:>8,.0f} "
            f"{m['taxable']:>10,.0f} {m['tax_charged']:>10,.0f} "
            f"{m['personal_relief']:>8,.0f} {m['paye']:>10,.0f}"
        )

    a = p9_data['annual_totals']
    lines.append("-" * 70)
    lines.append(
        f"{'ANNUAL':<12} {a['gross']:>10,.0f} {a['nssf']:>8,.0f} "
        f"{a['taxable']:>10,.0f} {a['tax_charged']:>10,.0f} "
        f"{a['personal_relief']:>8,.0f} {a['paye']:>10,.0f}"
    )
    lines.append("=" * 70)
    lines.append(f"Generated by KenyaComply | {p9_data['generated_at'][:10]}")

    return "\n".join(lines)


def generate_payslip_text(payslip, period, employer_name=''):
    """Generate downloadable payslip as text."""
    lines = []
    lines.append("=" * 50)
    lines.append("PAYSLIP")
    lines.append(f"Period: {period}")
    if employer_name:
        lines.append(f"Employer: {employer_name}")
    lines.append("=" * 50)
    lines.append(f"Employee: {payslip['name']}")
    lines.append(f"KRA PIN:  {payslip.get('kra_pin', 'N/A')}")
    lines.append("-" * 50)
    lines.append("EARNINGS:")
    lines.append(f"  Basic Salary:    KES {payslip['basic_salary']:>12,.2f}")
    if payslip.get('allowances', 0) > 0:
        lines.append(f"  Allowances:      KES {payslip['allowances']:>12,.2f}")
    lines.append(f"  GROSS PAY:       KES {payslip['gross_salary']:>12,.2f}")
    lines.append("-" * 50)
    lines.append("DEDUCTIONS:")
    lines.append(f"  NSSF:            KES {payslip['nssf']:>12,.2f}")
    lines.append(f"  PAYE:            KES {payslip['paye']:>12,.2f}")
    lines.append(f"  NHIF:            KES {payslip['nhif']:>12,.2f}")
    lines.append(f"  Total Deductions:KES {payslip['total_deductions']:>12,.2f}")
    lines.append("=" * 50)
    lines.append(f"  NET PAY:         KES {payslip['net_salary']:>12,.2f}")
    lines.append("=" * 50)
    lines.append("Generated by KenyaComply")
    return "\n".join(lines)
