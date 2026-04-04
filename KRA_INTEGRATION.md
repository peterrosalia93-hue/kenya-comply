# KenyaComply - KRA ETIMS Integration Guide

## Overview

KenyaComply can integrate with KRA's eTIMS (Electronic Tax Invoice Management System) to:
- Auto-submit invoices to KRA
- Sync with iTax
- Generate compliance reports

---

## KRA Integration Options

### Option 1: Manual Export (Available Now)
Generate invoice → Download → Upload manually to KRA portal

### Option 2: KRA API (Requires Registration)
**Requires:**
1. KRA Business Account (eCitizen)
2. EDRMS Integration Access (apply via KRA)
3. API Credentials (client ID + secret)

**Integration Steps:**
1. Apply for KRA API access via eCitizen
2. Receive credentials (test environment)
3. Implement REST API calls
4. Test with KRA sandbox
5. Go live

### Option 3: iTax Integration
- Auto-sync tax calculations to iTax
- File PAYE returns automatically
- Track filing status

---

## Current Invoice Format (KRA-Compliant)

The invoice generated includes:
- Invoice Number (KRA format)
- Seller KRA PIN
- Buyer KRA PIN  
- VAT at 16%
- Total Amount
- Date

---

## KRA API Implementation (Future)

```python
# Example KRA API call
import requests

KRA_API_URL = "https://api.kra.go.ke/etims/v1"

def submit_to_kra(invoice_data, api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    response = requests.post(
        f"{KRA_API_URL}/invoices",
        json=invoice_data,
        headers=headers
    )
    return response.json()
```

---

## M-Pesa Payment Integration

### Flutterwave Setup

1. **Create Flutterwave Account**
   - Go to flutterwave.com
   - Register business

2. **Get API Keys**
   - Secret Key
   - Public Key

3. **Integration**
   - Add payment button to invoice
   - Customer pays via STK push
   - Webhook confirms payment

---

## APK Build for Play Store

### Via EAS (Expo Application Services)

```bash
# Install EAS CLI
npm install -g eas-cli

# Login to Expo
eas login

# Configure
eas build:configure

# Build Android APK
eas build --platform android --profile preview
```

### Result
- `.apk` file (installable)
- Can upload to Google Play Console

---

## Next Steps

1. [x] Document KRA/M-Pesa options
2. [ ] Add PDF download
3. [ ] Add dashboard history
4. [ ] Add print view
5. [ ] Configure EAS build

---

*Generated: 2026-04-04*
*KenyaComply by Mwakulomba* 🎥📜