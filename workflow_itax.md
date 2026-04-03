# KRA iTax Workflow Mapping

## Overview
This document maps the iTax filing process to enable automation.

---

## 1. iTax Portal Access

**URL**: https://itax.kra.go.ke

### Login Flow
1. Navigate to iTax portal
2. Enter username (KRA PIN or email)
3. Enter password
4. Enter PIN (6-digit security PIN)
5. Handle CAPTCHA if present
6. Dashboard loads

### Authentication Methods
- **Primary**: PIN-based login
- **Alternative**: SMS OTP for sensitive operations

---

## 2. Tax Types and Forms

### A. PAYE (Pay As You Earn) — Form P10
**Frequency**: Monthly (by 10th of following month)
**Who files**: Employers

**Fields required**:
- Employer PIN
- Period (month/year)
- Employee details:
  - PIN
  - Gross salary
  - Benefits
  - Deductions (NSSF, NHIF, pension)
  - Tax charged
- Total tax due
- Payment reference number

### B. Value Added Tax (VAT) — Form KV1
**Frequency**: Monthly (by 20th of following month)
**Who files**: VAT-registered businesses

**Fields required**:
- Taxpayer PIN
- Tax period
- Output VAT
- Input VAT
- VAT adjustments
- Net VAT payable/refundable

### C. Income Tax — Form R1
**Frequency**: Annual (by 4th month after year-end)
**Who files**: All taxable persons

**Fields required**:
- Personal/Company details
- Income from all sources
- Allowable deductions
- Tax computation
- Losses brought forward

---

## 3. Filing Process Map

### Step-by-Step: PAYE Filing (P10)

```
1. Login to iTax
   → Dashboard loads
   
2. Navigate: Returns > Income Tax > PAYE > File P10
   → P10 form loads
   
3. Select period (Month/Year)
   → Form populates
   
4. Enter/import employee data
   → Can bulk upload CSV
   
5. System calculates tax automatically
   → Review totals
   
6. Submit return
   → Acknowledgment received
   
7. Generate payment slip
   → KRA payment reference
   
8. Make payment
   → Via M-Pesa, bank, etc.
```

### Step-by-Step: VAT Filing

```
1. Login to iTax
2. Navigate: Returns > VAT > File VAT
3. Select tax period
4. System auto-populates from ETIMS (if connected)
5. Review/adjust:
   - Output VAT
   - Input VAT
   - Adjustments
6. Submit return
7. Generate payment/refund
```

---

## 4. Field Mapping for Automation

### P10 Key Fields
| Field | iTax ID | Data Source |
|-------|---------|-------------|
| Employer PIN | emp_pin | Config |
| Period | tax_period | Input (YYYYMM) |
| Employee PIN | emp_pin | Employee DB |
| Gross Salary | gross_pay | Payroll |
| Benefits | benefits | Payroll |
| NSSF | nssf_ded | Payroll |
| Taxable Pay | taxable_pay | Calculated |
| Tax Charged | tax_charged | Calculated |

### VAT Key Fields
| Field | iTax ID | Data Source |
|-------|---------|-------------|
| Taxpayer PIN | pin | Config |
| Period | tax_period | Input |
| Output VAT | output_vat | ETIMS/Manual |
| Input VAT | input_vat | Purchases |
| Adjustments | adjustments | Manual |
| Net VAT | net_vat | Calculated |

---

## 5. Automation Strategy

### Approach A: Browser Automation (Playwright)
- **Pros**: No API approval needed
- **Cons**: Fragile, CAPTCHA risk, ToS concerns

**Steps**:
1. Launch browser (headless or visible)
2. Navigate to iTax
3. Handle login (credentials + PIN)
4. Navigate to form
5. Fill fields (direct input or CSV upload)
6. Submit
7. Capture confirmation

### Approach B: API Integration (Future)
- Apply for KRA API access
- Use official endpoints
- **Pros**: Stable, official, compliant
- **Cons**: Long approval process

### Approach C: Hybrid (Recommended)
- Use browser automation for form navigation
- Prepare data locally (calculator + ETIMS)
- Human review before final submit
- Capture confirmation

---

## 6. Current Status

- [x] Workflow mapping
- [x] Form field identification
- [ ] Browser automation scaffold
- [ ] CAPTCHA handling strategy
- [ ] Testing with sandbox account

---

## 7. Next Actions

1. Create Playwright automation scaffold (`itax_automation.py`)
2. Test login flow with test credentials
3. Map actual form field selectors
4. Handle CAPTCHA (manual intervention or solver)
5. Test submission with test data