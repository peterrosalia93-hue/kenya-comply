#!/usr/bin/env python3
"""
KenyaComply CLI - Command Line Interface
=========================================
All-in-one tool for Kenyan business compliance:
- ETIMS Invoice Generation
- Tax Calculations (PAYE, VAT)
- Business Registration Helpers
"""

import argparse
import json
import sys
from datetime import datetime

# Import our modules
try:
    from etims_invoice import create_standard_invoice, ETIMSInvoice
    from tax_calculator import calculate_paye, calculate_vat
except ImportError as e:
    print(f"Error: {e}")
    print("Make sure etims_invoice.py and tax_calculator.py are in the same directory.")
    sys.exit(1)


def cmd_invoice(args):
    """Generate ETIMS invoice"""
    items = [{"description": "Service", "quantity": 1, "unit_price": args.amount, "vat_rate": 16}]
    if args.items:
        items = eval(args.items)
    
    invoice = create_standard_invoice(
        seller_name=args.seller,
        seller_pin=args.seller_pin,
        seller_address=args.seller_address or "Nairobi, Kenya",
        seller_phone="+254700000000",
        buyer_name=args.buyer,
        buyer_pin=args.buyer_pin,
        buyer_address=args.buyer_address or "Kenya",
        items=items
    )
    
    print(f"\n{'='*50}")
    print("ETIMS INVOICE GENERATED")
    print(f"{'='*50}")
    print(f"Invoice Number: {invoice.invoice_number}")
    print(f"Date: {invoice.date}")
    print(f"Seller: {invoice.seller.name} ({invoice.seller.pin})")
    print(f"Buyer: {invoice.buyer.name} ({invoice.buyer.pin})")
    print(f"Items: {len(invoice.items)}")
    print(f"Subtotal: KES {invoice.subtotal:,.2f}")
    print(f"VAT (16%): KES {invoice.total_vat:,.2f}")
    print(f"Grand Total: KES {invoice.grand_total:,.2f}")
    print(f"{'='*50}")
    
    if args.json:
        print("\n--- JSON Export ---")
        print(json.dumps(invoice.to_kra_json(), indent=2))
    
    if args.xml:
        print("\n--- XML Export ---")
        print(invoice.to_xml())


def cmd_paye(args):
    """Calculate PAYE"""
    result = calculate_paye(args.salary)
    
    print(f"\n{'='*50}")
    print("PAYE CALCULATION")
    print(f"{'='*50}")
    print(f"Gross Salary: KES {result.gross_salary:,.2f}")
    print(f"NSSF:        KES {result.nssf:,.2f}")
    print(f"Taxable:     KES {result.taxable_income:,.2f}")
    print(f"Tax (before relief): KES {result.tax_before_relief:,.2f}")
    print(f"Personal Relief:     KES {result.personal_relief:,.2f}")
    print(f"Tax (after relief):  KES {result.tax_after_relief:,.2f}")
    print(f"NHIF:        KES {result.nhif:,.2f}")
    print(f"{'='*50}")
    print(f"NET SALARY:  KES {result.net_salary:,.2f}")
    print(f"{'='*50}")


def cmd_vat(args):
    """Calculate VAT"""
    result = calculate_vat(
        output_sales=args.sales,
        exempt_sales=args.exempt or 0,
        input_vat=args.input or 0
    )
    
    print(f"\n{'='*50}")
    print("VAT CALCULATION")
    print(f"{'='*50}")
    print(f"Output Sales:    KES {result.gross_sales:,.2f}")
    print(f"Exempt Sales:    KES {result.vat_exempt:,.2f}")
    print(f"VAT Collected:   KES {result.vat_collected:,.2f}")
    print(f"Input VAT:       KES {result.input_vat:,.2f}")
    print(f"{'='*50}")
    print(f"NET VAT PAYABLE: KES {result.net_vat_payable:,.2f}")
    print(f"{'='*50}")


def cmd_status(args):
    """Show KenyaComply status"""
    print(f"\n{'='*50}")
    print("KENYA COMPLY - STATUS")
    print(f"{'='*50}")
    print(f"Version: 1.0.0")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"\nModules:")
    print(f"  [x] ETIMS Invoice Generator")
    print(f"  [x] Tax Calculator (PAYE, VAT)")
    print(f"  [x] iTax Workflow Mapping")
    print(f"  [x] Business Registration Mapping")
    print(f"\n{'='*50}")


def main():
    parser = argparse.ArgumentParser(
        description="KenyaComply - Kenyan Business Compliance CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kenya_comply invoice --seller "My Company Ltd" --seller_pin P051234567A \\
                        --buyer "Client Ltd" --buyer_pin P098765432B --amount 50000
  
  kenya_comply paye --salary 250000
  
  kenya_comply vat --sales 100000 --input 10000
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Invoice command
    parser_invoice = subparsers.add_parser("invoice", help="Generate ETIMS invoice")
    parser_invoice.add_argument("--seller", required=True, help="Seller company name")
    parser_invoice.add_argument("--seller-pin", required=True, help="Seller KRA PIN")
    parser_invoice.add_argument("--seller-address", help="Seller address")
    parser_invoice.add_argument("--buyer", required=True, help="Buyer company name")
    parser_invoice.add_argument("--buyer-pin", required=True, help="Buyer KRA PIN")
    parser_invoice.add_argument("--buyer-address", help="Buyer address")
    parser_invoice.add_argument("--amount", type=float, required=True, help="Total amount")
    parser_invoice.add_argument("--items", help="Items as Python list")
    parser_invoice.add_argument("--json", action="store_true", help="Output JSON")
    parser_invoice.add_argument("--xml", action="store_true", help="Output XML")
    
    # PAYE command
    parser_paye = subparsers.add_parser("paye", help="Calculate PAYE tax")
    parser_paye.add_argument("--salary", type=float, required=True, help="Gross monthly salary")
    
    # VAT command
    parser_vat = subparsers.add_parser("vat", help="Calculate VAT")
    parser_vat.add_argument("--sales", type=float, required=True, help="Output sales")
    parser_vat.add_argument("--exempt", type=float, help="Exempt sales")
    parser_vat.add_argument("--input", type=float, help="Input VAT")
    
    # Status command
    parser_status = subparsers.add_parser("status", help="Show status")
    
    args = parser.parse_args()
    
    if args.command == "invoice":
        cmd_invoice(args)
    elif args.command == "paye":
        cmd_paye(args)
    elif args.command == "vat":
        cmd_vat(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
