# KenyaComply - M-Pesa Flutterwave Integration

"""
M-Pesa Payment Integration via Flutterwave
Handles STK push for KES 50 per invoice
"""

import os
import uuid
import json
from datetime import datetime

# Configure Flutterwave
FLUTTERWAVE_SECRET_KEY = os.environ.get('FLUTTERWAVE_SECRET_KEY', '')
FLUTTERWAVE_PUBLIC_KEY = os.environ.get('FLUTTERWAVE_PUBLIC_KEY', '')
FLUTTERWAVE_BASE_URL = 'https://api.flutterwave.com/v3'

# Demo mode (set to True for testing without real payments)
DEMO_MODE = True

def initiate_mpesa_payment(phone, amount, tx_ref=None):
    """
    Initiate M-Pesa STK push via Flutterwave
    
    Args:
        phone: Phone number (2547XX or 07XX format)
        amount: Amount in KES
        tx_ref: Transaction reference (auto-generated if not provided)
    
    Returns:
        dict with payment status
    """
    if tx_ref is None:
        tx_ref = f"KC_{uuid.uuid4().hex[:12]}"
    
    # Format phone number
    phone = phone.replace('+254', '254')
    if phone.startswith('07'):
        phone = '254' + phone[1:]
    
    if DEMO_MODE:
        # Demo mode - just return success
        return {
            "status": "success",
            "message": "Payment simulated (DEMO MODE)",
            "data": {
                "tx_ref": tx_ref,
                "flw_ref": f"FLW{uuid.uuid4().hex[:8]}",
                "amount": amount,
                "phone": phone
            }
        }
    
    # Real payment - would call Flutterwave API
    # This requires actual API keys to work
    payload = {
        "tx_ref": tx_ref,
        "amount": str(amount),
        "currency": "KES",
        "phone_number": phone,
        "network": "MPESA",
        "email": "customer@email.com",
        "fullname": "KenyaComply Customer",
        "description": "KenyaComply Invoice - KES 50",
        "is_mpesa": 1,
        "meta": {
            "invoice": "KenyaComply"
        }
    }
    
    headers = {
        "Authorization": f"Bearer {FLUTTERWAVE_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    # Would make actual API call here
    # import requests
    # response = requests.post(
    #     f"{FLUTTERWAVE_BASE_URL}/payments",
    #     json=payload,
    #     headers=headers
    # )
    # return response.json()
    
    return {"status": "pending", "message": "Configure API keys for real payments"}


def verify_mpesa_payment(tx_ref):
    """
    Verify M-Pesa payment status
    
    Args:
        tx_ref: Transaction reference
    
    Returns:
        dict with verification status
    """
    if DEMO_MODE:
        return {
            "status": "success",
            "message": "Payment verified (DEMO MODE)",
            "data": {
                "tx_ref": tx_ref,
                "status": "completed"
            }
        }
    
    # Real verification
    # Would call Flutterwave API to check status
    return {"status": "pending"}


# Payment configuration
PAYMENT_CONFIG = {
    "fee": 50,  # KES per invoice
    "currency": "KES",
    "network": "MPESA",
    "demo_mode": DEMO_MODE
}