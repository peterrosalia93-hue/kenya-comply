# eCitizen Business Registration Workflow Mapping

## Overview
This document maps the Kenyan business/company registration process via eCitizen/BRS for automation.

---

## 1. eCitizen Portal Access

**URL**: https://www.ecitizen.go.ke

### Login Flow
1. Navigate to eCitizen
2. Click "Login" or "Sign In"
3. Enter username (email or national ID)
4. Enter password
5. Dashboard loads
6. Select "Business Registration Service (BRS)"

---

## 2. Registration Paths

### A. Business Name (Sole Proprietorship)
- Simplest form
- No minimum capital
- No shareholder requirements

### B. Private Limited Company (Ltd)
- Most common for SMEs
- 1-50 shareholders
- At least 1 director (1 must be Kenyan resident)
- Minimum share capital: KSh 1

### C. Public Company (PLC)
- Minimum 2 shareholders
- At least 2 directors
- Higher capital requirements

### D. Partnership
- 2-20 partners
- No limit on liability type

---

## 3. Step-by-Step: Private Limited Company

### Phase 1: Name Reservation

```
1. Login to eCitizen
2. Navigate: BRS > Name Reservation
3. Enter proposed names (up to 3, priority order)
4. Pay KSh 150 via M-Pesa/Card
5. Submit
6. Wait 1-2 working days for approval
7. Download name approval letter (valid 30 days)
```

**Fields**:
- Proposed Name 1
- Proposed Name 2 (optional)
- Proposed Name 3 (optional)
- Business activity description
- Applicant details

---

### Phase 2: Company Registration

```
1. Login to eCitizen
2. Navigate: BRS > Register Company > Private Limited Company
3. Select name from approved list
4. Fill CR1 (Application for Registration)
   - Company name
   - Registered office address
   - Principal place of business
   - Nature of business
   - Director details
   - Shareholder details
   - Share capital
5. Fill CR2 (Statement of Nominal Capital)
   - Authorized share capital
   - Classes of shares
   - Number of shares
6. Fill CR8 (Notice of Registered Office)
   - Physical address
   - Postal address
   - County
7. Upload documents:
   - ID copies of all directors
   - KRA PINs of all directors
   - Passport photos of directors
8. Fill BOF1 (Beneficial Owners)
   - List all beneficial owners
   - Nationality, ID, ownership %
9. Pay registration fee (KSh 10,000-12,000 + stamp duty)
10. Submit
11. Wait ~7-21 days for approval
12. Download Certificate of Incorporation
```

---

## 4. Form Field Mapping

### CR1 - Key Fields
| Field | Description | Automation |
|-------|-------------|------------|
| company_name | From approved list | Auto-fill |
| reg_office_address | Physical address | Input |
| postal_address | PO Box, etc. | Input |
| county | County location | Dropdown |
| business_nature | Nature of business | Dropdown/Input |
| director_1_name | Full name | Input |
| director_1_id | National ID/Passport | Input |
| director_1_pin | KRA PIN | Input |
| director_1_nationality | Country | Dropdown |
| director_1_dob | Date of birth | Input |
| shareholder_1_name | Name | Input |
| shareholder_1_shares | Number of shares | Input |
| secretary | (Optional) Details | Input |

### CR2 - Key Fields
| Field | Description |
|-------|-------------|
| nominal_capital | Authorized share capital |
| share_class | Ordinary/Preference |
| share_currency | KES |

### CR8 - Key Fields
| Field | Description |
|-------|-------------|
| physical_address | Street/Building |
| postal_address | PO Box |
| county | County |
| district | District |
| town | Town |

### BOF1 - Key Fields
| Field | Description |
|-------|-------------|
| owner_name | Full name |
| owner_id | ID number |
| owner_pin | KRA PIN |
| ownership_pct | Percentage |
| nationality | Country |

---

## 5. Fees and Timeline

| Item | Cost (KES) | Timeline |
|------|------------|----------|
| Name Reservation | 150 | 1-2 days |
| Company Registration | 10,000-12,000 | 7-21 days |
| Stamp Duty | ~0.5% of capital | Included |
| Business Permit (County) | Varies | After registration |
| NSSF | 200/month | After registration |
| SHA (Health) | Varies | After registration |

---

## 6. Automation Strategy

### Approach A: Browser Automation (Playwright)
- **Pros**: No API needed
- **Cons**: Complex form handling, upload issues, session management

**Process**:
1. Login to eCitizen
2. Navigate to Name Reservation
3. Fill name proposal form
4. Submit payment (M-Pesa requires manual step)
5. Navigate to Company Registration
6. Fill CR1/CR2/CR8
7. Upload documents
8. Submit
9. Capture confirmation

### Approach B: Data Preparation First
- Build form-filling assistant (not full automation)
- User enters data in our tool
- We generate filled PDFs
- User uploads manually to eCitizen
- **This is more practical short-term**

### Approach C: Future Integration
- Apply for BRS API access
- Official integration
- **Pros**: Full automation possible
- **Cons**: Unknown availability/approval

---

## 7. Data Models for Automation

### CompanyData
```python
{
    "company_name": str,
    "approved_name_date": str,
    "registered_address": {
        "building": str,
        "street": str,
        "county": str,
        "district": str,
        "postal_address": str
    },
    "directors": [
        {
            "name": str,
            "id_number": str,
            "pin": str,
            "nationality": str,
            "dob": str,
            "email": str,
            "phone": str
        }
    ],
    "shareholders": [
        {
            "name": str,
            "shares": int,
            "nationality": str
        }
    ],
    "capital": {
        "nominal": int,
        "currency": "KES"
    },
    "beneficial_owners": [
        {
            "name": str,
            "id": str,
            "pin": str,
            "ownership_pct": float
        }
    ]
}
```

---

## 8. Current Status

- [x] Workflow mapping complete
- [x] Form field identification
- [ ] Form builder/generator
- [ ] Document upload handler
- [ ] Payment flow integration
- [ ] Browser automation scaffold

---

## 9. Next Actions

1. Create form generator that outputs filled forms
2. Build company data model
3. Create document checklist generator
4. Build Playwright scaffold for eCitizen
5. Test with sample company data