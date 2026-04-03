# Kenya Business Compliance Agent — SPEC.md

## Project Name
**KenyaComply** — AI Agent for Kenyan Business Compliance

## Vision
An AI-powered agent that automates:
1. KRA tax filing (iTax)
2. ETIMS e-invoicing
3. Business/company registration (eCitizen/BRS)
4. Post-registration compliance (permits, NSSF, SHA)

---

## Module Overview

### Module A: KRA Tax Agent

#### Features
1. **Tax Calculator**
   - PAYE (Pay As You Earn) calculation from salary inputs
   - VAT calculation (16% standard rate)
   - Income tax estimation
   - Auto-categorization of deductions

2. **ETIMS Invoice Generator**
   - Generate KRA-compliant e-invoices
   - Support for: Standard, Simplified, Credit Note, Debit Note
   - XML/JSON export for KRA submission
   - Validation against KRA schema

3. **iTax Filing Assistant**
   - Guide through filing process
   - Auto-fill forms (P10, R1, VAT returns)
   - Status tracking and reminders

#### Tech Stack
- Python (core logic)
- Playwright (browser automation for iTax)
- KRA API (ETIMS) — requires certification or simulation mode
- SQLite/JSON (data persistence)

---

### Module B: Business Registration Agent

#### Features
1. **Name Reservation**
   - Name availability check
   - Submit reservation via eCitizen
   - Track approval status

2. **Company Registration**
   - Auto-fill CR1, CR2, CR8 forms
   - Directors/shareholders details
   - Registered office address
   - Beneficial owners (BOF1)

3. **Post-Registration**
   - Business permit application
   - NSSF registration
   - SHA (Social Health Authority) registration

#### Tech Stack
- Python
- Playwright (eCitizen automation)
- PDF generation (filled forms)
- Data validation engine

---

## MVP Roadmap

### Phase 1 — ETIMS Invoice Generator (Week 1-2)
- [x] Invoice data model
- [ ] KRA schema validation
- [ ] XML/JSON export
- [ ] UI for manual entry

### Phase 2 — Tax Calculator (Week 3)
- [ ] PAYE calculator
- [ ] VAT calculator
- [ ] Tax liability summary

### Phase 3 — iTax Workflow Mapping (Week 4)
- [ ] Form field mapping (P10, R1, VAT)
- [ ] Login/automation flow
- [ ] CAPTCHA handling strategy

### Phase 4 — Business Registration (Week 5-6)
- [ ] eCitizen name reservation flow
- [ ] CR1/CR2/CR8 auto-fill
- [ ] Document upload handling

### Phase 5 — Full Integration (Week 7-8)
- [ ] Combine all modules
- [ ] User dashboard
- [ ] Compliance reminders

---

## Key Data Models

### Invoice
```
- invoice_number (unique)
- date
- seller (name, PIN, address, phone)
- buyer (name, PIN, address)
- items (description, quantity, unit_price, VAT rate)
- totals (subtotal, VAT, grand_total)
- type (standard/simplified/credit/debit)
```

### Company
```
- name
- registration_number
- registered_address
- directors (list)
- shareholders (list)
- share_capital
- business_activities
```

### TaxEntry
```
- period (month/year)
- type (PAYE/VAT/Income)
- amount
- status (pending/filed/paid)
- due_date
```

---

## Compliance Requirements

### KRA ETIMS
- Invoice must include: Seller PIN, Buyer PIN, Invoice number, Date, Items with VAT breakdown
- Real-time transmission requires KRA API (certified software)
- Offline mode: export XML, upload manually

### eCitizen/BRS
- Name reservation: KSh 150
- Company registration: KSh 10,000-12,000 + stamp duty
- Documents: ID copies, KRA PINs, photos

### iTax
- Filing deadlines: Monthly (10th), Quarterly (15th), Annual (4th month after year-end)
- PIN-based authentication

---

## Current Status
- [x] SPEC created
- [x] ETIMS invoice generator - DONE (CLI working)
- [x] Tax calculator - DONE (CLI working)
- [x] CLI interface - DONE
- [ ] iTax browser automation scaffold
- [ ] Business registration form builder
- [ ] Web interface (optional)

---

## Next Actions
1. Build ETIMS invoice generator (`etims_invoice.py`)
2. Map all iTax form fields
3. Map eCitizen registration steps
4. Create Playwright automation scaffolds