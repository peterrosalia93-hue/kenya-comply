# KRA Tax Filing Guide - Kenya

## Overview

This guide covers how to file KRA tax returns for individuals and businesses in Kenya via iTax.

---

## iTax Portal Access

**URL:** https://itax.kra.go.ke

**Login:**
1. Username: Your KRA PIN or email
2. Password: Set during registration

**First Time?**
- Register at eCitizen → KRA services → iTax Registration

---

## Tax Types & Deadlines

| Tax Type | Who Files | Deadline |
|---------|----------|----------|
| **PAYE** | Employers | 30th of next month |
| **income Tax** | Individuals | 30th April annually |
| **Corporate Tax** | Companies | 30th June annually |
| **VAT** | VAT-registered | 20th of next month |
| **Excise Duty** | Excise taxpayers | 20th of next month |

---

## How to File Income Tax (Individual)

### Step 1: Login to iTax
1. Go to https://itax.kra.go.ke
2. Enter PIN + password
3. Complete 2FA

### Step 2: Select Return Type
1. Click **Returns** → **Income Tax**
2. Select **Self Assessment** (for employees)
3. Choose tax year (e.g., 2025)

### Step 3: Fill the Form

**Section A: Personal Details**
- KRA PIN ✓
- Name ✓
- Employment status

**Section B: Income**
- Gross salary (from P9 form)
- Benefitsallowances
- Other income

**Section C: Deductions**
- Retirement contributions (max KES 300,000)
- Insurance premiums (max KES 60,000)
- Mortgage interest (max KES 300,000)

**Section D: Tax Computed**
- Taxable income = Gross - Deductions
- Tax = Apply tax bands (see below)

### Tax Bands 2025

| Income (KES) | Rate |
|-------------|------|
| 0 - 288,000 | 10% |
| 288,001 - 388,000 | 25% |
| 388,001 - 550,000 | 30% |
| 550,001+ | 35% |

### Step 4: Submit
1. Review calculations
2. Click **Submit**
3. Note the compliance certificate number

---

## How to File PAYE (Employer)

### Monthly Remittance

1. **P10 Form** → Calculate employee tax
2. **Monthly PAYE** → 30th of next month
3. File via iTax or **eLevy** system

### Code
- Use tax tables or software
- Submit via API (for developers)

---

## How to File Corporate Tax (Company)

### Annual Returns

1. **Corporate Tax** filing deadline: 30th June
2. **Installment Tax**: Quarterly (4th, 6th, 9th, 12th month)

### Tax Rate
- **Companies**: 30% of taxable income
- **Turnover < KES 500M**: 25% (SMEs)

---

## How to File VAT

### Registration
- Mandatory if turnover > KES 5M/year
- Can voluntarily register

### Filing
- **Standard rate**: 16%
- **Zero-rated**: 0%
- File monthly by 20th

### Via API
- Use KRA eTIMS API
- KenyaComply format ready!

---

## KenyaComply + KRA Integration

### Current Features
| Feature | Status |
|---------|--------|
| Generate ETIMS Invoice | ✅ |
| Download for KRA | ✅ |
| Manual upload to KRA | ✅ |

### Future (API Required)
| Feature | Requires |
|---------|----------|
| Auto-submit to KRA | KRA API keys |
| iTax sync | KRA API keys |
| PAYE filing | Payroll integration |

### Invoice → KRA Flow
1. Generate invoice in KenyaComply
2. Download as .txt/.pdf
3. Upload to KRA via portal or API

---

## Tax Compliance Certificates

| Certificate | Required For | How |
|------------|------------|-----|
| Tax Compliance | Tenders, licenses | Download from iTax |
| Withholding | Withholding agents | File monthly |
| Excise | Excise taxpayers | File monthly |

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| Invalid PIN | Check registration |
| Wrong tax type | Select correct return |
| Late penalty | File early |
| Math error | Use tax calculator |

---

## Contact KRA

- **Call:** 020-281-1100
- **Email:** callcentre@kra.go.ke
- **WhatsApp:** 072-888-1111

---

*Guide by KenyaComply - 2026-04-04*