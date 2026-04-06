# KenyaComply - M-Pesa Daraja API Integration
# Safaricom STK Push (Lipa Na M-Pesa Online)

import os
import uuid
import json
import base64
from datetime import datetime

try:
    import requests as http_requests
except ImportError:
    http_requests = None

# ============================================
# CONFIGURATION
# ============================================
# Safaricom Daraja API credentials (set in environment)
MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET', '')
MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE', '174379')  # Sandbox default
MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')
MPESA_CALLBACK_URL = os.environ.get('MPESA_CALLBACK_URL', '')
MPESA_ENV = os.environ.get('MPESA_ENV', 'sandbox')  # 'sandbox' or 'production'

# API URLs
SANDBOX_URL = 'https://sandbox.safaricom.co.ke'
PRODUCTION_URL = 'https://api.safaricom.co.ke'
BASE_URL = PRODUCTION_URL if MPESA_ENV == 'production' else SANDBOX_URL

# Demo mode when no credentials are set
DEMO_MODE = not (MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET)

# Payment store (in-memory for Vercel; replace with DB in production)
PAYMENTS = {}

PAYMENT_CONFIG = {
    "fee": 50,
    "currency": "KES",
    "network": "MPESA",
    "demo_mode": DEMO_MODE,
    "shortcode": MPESA_SHORTCODE
}


# ============================================
# AUTH - Get OAuth Token
# ============================================
def get_access_token():
    """Get M-Pesa OAuth access token from Daraja API."""
    if DEMO_MODE or not http_requests:
        return None

    url = f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
    credentials = base64.b64encode(
        f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}".encode()
    ).decode()

    try:
        resp = http_requests.get(
            url,
            headers={"Authorization": f"Basic {credentials}"},
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception as e:
        print(f"[M-Pesa] Auth error: {e}")
    return None


def generate_password():
    """Generate the Daraja API password (Shortcode + Passkey + Timestamp)."""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    raw = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
    password = base64.b64encode(raw.encode()).decode()
    return password, timestamp


# ============================================
# STK PUSH - Lipa Na M-Pesa Online
# ============================================
def initiate_mpesa_payment(phone, amount, account_ref="KenyaComply", tx_ref=None):
    """
    Initiate M-Pesa STK Push payment.

    Args:
        phone: Kenyan phone number (07XX, 01XX, or 2547XX format)
        amount: Amount in KES (integer)
        account_ref: Account reference shown on M-Pesa prompt
        tx_ref: Optional transaction reference

    Returns:
        dict with payment status and details
    """
    if tx_ref is None:
        tx_ref = f"KC_{uuid.uuid4().hex[:12]}"

    # Normalize phone number to 2547XXXXXXXX
    phone = str(phone).replace(' ', '').replace('+', '')
    if phone.startswith('07') or phone.startswith('01'):
        phone = '254' + phone[1:]
    elif phone.startswith('7') or phone.startswith('1'):
        phone = '254' + phone
    elif not phone.startswith('254'):
        phone = '254' + phone

    amount = int(amount)

    # Store payment record
    PAYMENTS[tx_ref] = {
        "tx_ref": tx_ref,
        "phone": phone,
        "amount": amount,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "mpesa_receipt": None,
        "checkout_request_id": None
    }

    # DEMO MODE
    if DEMO_MODE:
        PAYMENTS[tx_ref]["status"] = "completed"
        PAYMENTS[tx_ref]["mpesa_receipt"] = f"QJ{uuid.uuid4().hex[:8].upper()}"
        return {
            "status": "success",
            "message": "STK Push sent (DEMO MODE). Check your phone.",
            "data": {
                "tx_ref": tx_ref,
                "checkout_request_id": f"ws_CO_{uuid.uuid4().hex[:16]}",
                "amount": amount,
                "phone": phone,
                "demo": True
            }
        }

    # REAL M-PESA STK PUSH
    token = get_access_token()
    if not token:
        return {"status": "error", "message": "Failed to authenticate with M-Pesa"}

    password, timestamp = generate_password()
    callback = MPESA_CALLBACK_URL or f"https://kenya-comply.vercel.app/api/mpesa/callback"

    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": callback,
        "AccountReference": account_ref,
        "TransactionDesc": f"KenyaComply Invoice - KES {amount}"
    }

    try:
        resp = http_requests.post(
            f"{BASE_URL}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        result = resp.json()

        if result.get("ResponseCode") == "0":
            PAYMENTS[tx_ref]["checkout_request_id"] = result.get("CheckoutRequestID")
            return {
                "status": "success",
                "message": "STK Push sent. Check your phone to enter M-Pesa PIN.",
                "data": {
                    "tx_ref": tx_ref,
                    "checkout_request_id": result.get("CheckoutRequestID"),
                    "merchant_request_id": result.get("MerchantRequestID"),
                    "amount": amount,
                    "phone": phone
                }
            }
        else:
            return {
                "status": "error",
                "message": result.get("errorMessage", result.get("ResponseDescription", "STK Push failed")),
                "data": result
            }
    except Exception as e:
        return {"status": "error", "message": f"M-Pesa request failed: {str(e)}"}


# ============================================
# VERIFY PAYMENT
# ============================================
def verify_mpesa_payment(tx_ref):
    """Check payment status by transaction reference."""
    payment = PAYMENTS.get(tx_ref)
    if not payment:
        return {"status": "error", "message": "Transaction not found"}

    if payment["status"] == "completed":
        return {
            "status": "success",
            "message": "Payment confirmed",
            "data": {
                "tx_ref": tx_ref,
                "status": "completed",
                "mpesa_receipt": payment.get("mpesa_receipt"),
                "amount": payment["amount"]
            }
        }

    # Try STK Query for real payments
    if not DEMO_MODE and payment.get("checkout_request_id"):
        return query_stk_status(payment["checkout_request_id"], tx_ref)

    return {
        "status": "pending",
        "message": "Payment not yet confirmed",
        "data": {"tx_ref": tx_ref, "status": payment["status"]}
    }


def query_stk_status(checkout_request_id, tx_ref):
    """Query the status of an STK Push from Safaricom."""
    token = get_access_token()
    if not token:
        return {"status": "error", "message": "Auth failed"}

    password, timestamp = generate_password()

    try:
        resp = http_requests.post(
            f"{BASE_URL}/mpesa/stkpushquery/v1/query",
            json={
                "BusinessShortCode": MPESA_SHORTCODE,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=15
        )
        result = resp.json()

        if result.get("ResultCode") == "0":
            PAYMENTS[tx_ref]["status"] = "completed"
            return {
                "status": "success",
                "message": "Payment confirmed by M-Pesa",
                "data": {"tx_ref": tx_ref, "status": "completed"}
            }
        elif result.get("ResultCode") == "1032":
            PAYMENTS[tx_ref]["status"] = "cancelled"
            return {"status": "cancelled", "message": "Payment cancelled by user"}
        else:
            return {
                "status": "pending",
                "message": result.get("ResultDesc", "Still processing"),
                "data": {"tx_ref": tx_ref, "status": "pending"}
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================
# CALLBACK HANDLER
# ============================================
def process_mpesa_callback(callback_data):
    """Process M-Pesa callback from Safaricom."""
    body = callback_data.get("Body", {}).get("stkCallback", {})
    result_code = body.get("ResultCode")
    checkout_id = body.get("CheckoutRequestID")

    # Find the payment by checkout_request_id
    tx_ref = None
    for ref, payment in PAYMENTS.items():
        if payment.get("checkout_request_id") == checkout_id:
            tx_ref = ref
            break

    if not tx_ref:
        return {"status": "error", "message": "Payment not found"}

    if result_code == 0:
        # Success - extract receipt number
        items = body.get("CallbackMetadata", {}).get("Item", [])
        receipt = None
        for item in items:
            if item.get("Name") == "MpesaReceiptNumber":
                receipt = item.get("Value")

        PAYMENTS[tx_ref]["status"] = "completed"
        PAYMENTS[tx_ref]["mpesa_receipt"] = receipt
        return {"status": "success", "tx_ref": tx_ref, "receipt": receipt}
    else:
        PAYMENTS[tx_ref]["status"] = "failed"
        return {"status": "failed", "message": body.get("ResultDesc")}
