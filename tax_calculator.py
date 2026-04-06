# Tax Calculator for Kenya
# PAYE (Pay As You Earn), VAT, and Income Tax calculations

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

# KRA Tax Bands 2024 (Monthly)
TAX_BANDS = [
    (240000, 0.10),      # First 240,000: 10%
    (240001, 320000, 0.15),  # 240,001 - 320,000: 15%
    (320001, 400000, 0.20),  # 320,001 - 400,000: 20%
    (400001, 500000, 0.25),  # 400,001 - 500,000: 25%
    (500001, 800000, 0.30),  # 500,001 - 800,000: 30%
    (800001, float('inf'), 0.35)  # Above 800,000: 35%
]

# NHIF Contributions (2024)
NHIF_RATES = [
    (5999, 150),
    (7999, 300),
    (11999, 400),
    (14999, 500),
    (19999, 600),
    (24999, 750),
    (29999, 850),
    (34999, 900),
    (39999, 950),
    (44999, 1000),
    (49999, 1100),
    (59999, 1200),
    (69999, 1300),
    (79999, 1400),
    (89999, 1500),
    (99999, 1600),
    (119999, 1700),
    (139999, 1800),
    (199999, 2000),
    (249999, 2500),
    (299999, 3000),
    (399999, 3500),
    (499999, 4000),
    (599999, 4500),
    (699999, 5000),
    (799999, 5500),
    (899999, 6000),
    (999999, 6500),
    (float('inf'), 7000)
]

# NSSF Contribution (2024) - New rates
NSSF_RATE = 0.06  # 6% (employee 6%, employer 6%) - capped at KSh 2,160/month


@dataclass
class PAYEResult:
    gross_salary: float
    nssf: float
    taxable_income: float
    tax_before_relief: float
    personal_relief: float  # KSh 2,400/month
    tax_after_relief: float
    nhif: float
    net_salary: float
    
    def to_dict(self) -> dict:
        return {
            "gross_salary": round(self.gross_salary, 2),
            "nssf": round(self.nssf, 2),
            "taxable_income": round(self.taxable_income, 2),
            "tax_before_relief": round(self.tax_before_relief, 2),
            "personal_relief": round(self.personal_relief, 2),
            "tax_after_relief": round(self.tax_after_relief, 2),
            "nhif": round(self.nhif, 2),
            "net_salary": round(self.net_salary, 2)
        }


def calculate_paye(gross_salary: float) -> PAYEResult:
    """Calculate PAYE given gross monthly salary"""
    
    # Calculate NSSF (capped at KSh 2,160)
    nssf = min(gross_salary * NSSF_RATE, 2160)
    
    # Taxable income after NSSF
    taxable_income = gross_salary - nssf
    
    # Calculate tax based on bands
    tax = 0
    remaining = taxable_income
    
    # Band 1: 0 - 240,000 @ 10%
    if remaining > 0:
        band1 = min(remaining, 240000)
        tax += band1 * 0.10
        remaining -= band1
    
    # Band 2: 240,001 - 320,000 @ 15%
    if remaining > 0:
        band2 = min(remaining, 80000)
        tax += band2 * 0.15
        remaining -= band2
    
    # Band 3: 320,001 - 400,000 @ 20%
    if remaining > 0:
        band3 = min(remaining, 80000)
        tax += band3 * 0.20
        remaining -= band3
    
    # Band 4: 400,001 - 500,000 @ 25%
    if remaining > 0:
        band4 = min(remaining, 100000)
        tax += band4 * 0.25
        remaining -= band4
    
    # Band 5: 500,001 - 800,000 @ 30%
    if remaining > 0:
        band5 = min(remaining, 300000)
        tax += band5 * 0.30
        remaining -= band5
    
    # Band 6: Above 800,000 @ 35%
    if remaining > 0:
        tax += remaining * 0.35
    
    tax_before_relief = tax
    
    # Apply personal relief (KSh 2,400/month)
    personal_relief = 2400
    tax_after_relief = max(0, tax_before_relief - personal_relief)
    
    # Calculate NHIF
    nhif = calculate_nhif(gross_salary)
    
    # Net salary
    net_salary = gross_salary - nssf - tax_after_relief - nhif
    
    return PAYEResult(
        gross_salary=gross_salary,
        nssf=nssf,
        taxable_income=taxable_income,
        tax_before_relief=tax_before_relief,
        personal_relief=personal_relief,
        tax_after_relief=tax_after_relief,
        nhif=nhif,
        net_salary=net_salary
    )


def calculate_nhif(gross: float) -> float:
    """Calculate NHIF contribution based on gross salary"""
    for threshold, contribution in NHIF_RATES:
        if gross <= threshold:
            return contribution
    return 7000  # Max contribution


@dataclass
class VATResult:
    gross_sales: float
    vat_collected: float
    vat_exempt: float
    total_vat_liable: float
    input_vat: float
    net_vat_payable: float


def calculate_vat(
    output_sales: float,
    exempt_sales: float = 0,
    input_vat: float = 0
) -> VATResult:
    """Calculate VAT liability"""
    
    # Standard rated sales (assuming all non-exempt is standard rated)
    standard_sales = output_sales - exempt_sales
    
    # VAT collected on standard sales (16%)
    vat_collected = standard_sales * 0.16
    
    # Total VAT liable
    total_vat_liable = vat_collected
    
    # Net VAT payable (output VAT - input VAT)
    net_vat_payable = max(0, vat_collected - input_vat)
    
    return VATResult(
        gross_sales=output_sales,
        vat_collected=vat_collected,
        vat_exempt=exempt_sales,
        total_vat_liable=total_vat_liable,
        input_vat=input_vat,
        net_vat_payable=net_vat_payable
    )


# ============================================
# CORPORATE TAX
# ============================================
@dataclass
class CorporateTaxResult:
    gross_income: float
    allowable_expenses: float
    taxable_income: float
    tax_rate: float
    tax_payable: float
    installments_paid: float
    balance_due: float

def calculate_corporate_tax(
    gross_income: float,
    allowable_expenses: float = 0,
    is_sme: bool = False,
    installments_paid: float = 0
) -> CorporateTaxResult:
    """Calculate Corporate Tax. SME rate 25%, standard 30%."""
    taxable = max(0, gross_income - allowable_expenses)
    rate = 0.25 if is_sme else 0.30
    tax = taxable * rate
    balance = max(0, tax - installments_paid)
    return CorporateTaxResult(
        gross_income=gross_income, allowable_expenses=allowable_expenses,
        taxable_income=taxable, tax_rate=rate * 100,
        tax_payable=tax, installments_paid=installments_paid,
        balance_due=balance
    )


# ============================================
# TURNOVER TAX (TOT)
# ============================================
@dataclass
class TurnoverTaxResult:
    gross_turnover: float
    tax_rate: float
    tax_payable: float

def calculate_turnover_tax(gross_turnover: float) -> TurnoverTaxResult:
    """
    Turnover Tax for businesses with annual turnover < KES 25M.
    Rate: 3% of gross turnover (effective from Jan 2023).
    """
    rate = 0.03
    tax = gross_turnover * rate
    return TurnoverTaxResult(
        gross_turnover=gross_turnover, tax_rate=3.0, tax_payable=tax
    )


# ============================================
# WITHHOLDING TAX
# ============================================
WITHHOLDING_RATES = {
    'dividends_resident': 5,
    'dividends_non_resident': 15,
    'interest_resident': 15,
    'interest_non_resident': 15,
    'royalties_resident': 5,
    'royalties_non_resident': 20,
    'management_fees_resident': 5,
    'management_fees_non_resident': 20,
    'professional_fees_resident': 5,
    'professional_fees_non_resident': 20,
    'contractual_fees_resident': 3,
    'rent_resident': 10,
    'insurance_commission': 10,
}

@dataclass
class WithholdingTaxResult:
    gross_amount: float
    tax_type: str
    rate: float
    tax_amount: float
    net_amount: float

def calculate_withholding_tax(amount: float, tax_type: str) -> WithholdingTaxResult:
    """Calculate Withholding Tax based on payment type."""
    rate = WITHHOLDING_RATES.get(tax_type, 5)
    tax = amount * (rate / 100)
    return WithholdingTaxResult(
        gross_amount=amount, tax_type=tax_type.replace('_', ' ').title(),
        rate=rate, tax_amount=tax, net_amount=amount - tax
    )


def generate_tax_summary(paye_result: PAYEResult) -> str:
    """Generate a human-readable tax summary"""
    summary = f"""
╔══════════════════════════════════════════════════════════════╗
║                    KENYA TAX SUMMARY                        ║
║                    {datetime.now().strftime('%B %Y')}                            ║
╠══════════════════════════════════════════════════════════════╣
║ GROSS SALARY              KES {paye_result.gross_salary:>14,.2f}          ║
╠══════════════════════════════════════════════════════════════╣
║ Deductions:                                                  ║
║   NSSF                    KES {paye_result.nssf:>14,.2f}          ║
║   NHIF                    KES {paye_result.nhif:>14,.2f}          ║
║   Tax (after relief)      KES {paye_result.tax_after_relief:>14,.2f}          ║
╠══════════════════════════════════════════════════════════════╣
║ TAXABLE INCOME           KES {paye_result.taxable_income:>14,.2f}          ║
║ Tax Before Relief        KES {paye_result.tax_before_relief:>14,.2f}          ║
║ Personal Relief          KES {paye_result.personal_relief:>14,.2f}          ║
╠══════════════════════════════════════════════════════════════╣
║ NET SALARY               KES {paye_result.net_salary:>14,.2f}          ║
╚══════════════════════════════════════════════════════════════╝
"""
    return summary


# Example usage
if __name__ == "__main__":
    # Test PAYE calculation
    print("=" * 60)
    print("PAYE CALCULATOR TEST")
    print("=" * 60)
    
    test_salaries = [50000, 100000, 250000, 500000, 1000000]
    
    for salary in test_salaries:
        result = calculate_paye(salary)
        print(f"\n--- Gross Salary: KES {salary:,.0f} ---")
        print(f"NSSF:     KES {result.nssf:,.2f}")
        print(f"Tax:      KES {result.tax_after_relief:,.2f}")
        print(f"NHIF:     KES {result.nhif:,.2f}")
        print(f"Net:      KES {result.net_salary:,.2f}")
    
    # Test VAT calculation
    print("\n" + "=" * 60)
    print("VAT CALCULATOR TEST")
    print("=" * 60)
    
    vat_result = calculate_vat(
        output_sales=100000,
        exempt_sales=10000,
        input_vat=5000
    )
    
    print(f"\nOutput Sales:     KES {vat_result.gross_sales:,.2f}")
    print(f"Exempt Sales:    KES {vat_result.vat_exempt:,.2f}")
    print(f"VAT Collected:   KES {vat_result.vat_collected:,.2f}")
    print(f"Input VAT:        KES {vat_result.input_vat:,.2f}")
    print(f"Net VAT Payable: KES {vat_result.net_vat_payable:,.2f}")