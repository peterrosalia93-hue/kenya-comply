# ETIMS Invoice Generator
# Generates KRA-compliant e-invoices for Kenyan businesses
# Supports: Standard, Simplified, Credit Note, Debit Note

import json
import uuid
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, asdict

@dataclass
class Party:
    name: str
    pin: str  # KRA PIN
    address: str
    phone: str
    email: str = ""

@dataclass
class InvoiceItem:
    description: str
    quantity: float
    unit_price: float
    vat_rate: float = 16.0  # Default 16% VAT
    
    @property
    def total_exclusive(self) -> float:
        return self.quantity * self.unit_price
    
    @property
    def vat_amount(self) -> float:
        return self.total_exclusive * (self.vat_rate / 100)
    
    @property
    def total_inclusive(self) -> float:
        return self.total_exclusive + self.vat_amount

@dataclass
class ETIMSInvoice:
    invoice_number: str
    date: str  # ISO format
    seller: Party
    buyer: Party
    items: List[InvoiceItem]
    invoice_type: str = "standard"  # standard, simplified, credit, debit
    
    def __post_init__(self):
        if not self.invoice_number:
            self.invoice_number = self._generate_invoice_number()
    
    def _generate_invoice_number(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"INV-{timestamp}-{uuid.uuid4().hex[:6].upper()}"
    
    @property
    def subtotal(self) -> float:
        return sum(item.total_exclusive for item in self.items)
    
    @property
    def total_vat(self) -> float:
        return sum(item.vat_amount for item in self.items)
    
    @property
    def grand_total(self) -> float:
        return self.subtotal + self.total_vat
    
    def to_kra_json(self) -> dict:
        """Convert to KRA ETIMS JSON format"""
        return {
            "Invoice": {
                "Header": {
                    "InvoiceNumber": self.invoice_number,
                    "InvoiceDate": self.date,
                    "InvoiceType": self.invoice_type.upper(),
                    "InvoiceCurrency": "KES"
                },
                "Seller": {
                    "SellerName": self.seller.name,
                    "SellerPIN": self.seller.pin,
                    "SellerAddress": self.seller.address,
                    "SellerPhone": self.seller.phone,
                    "SellerEmail": self.seller.email
                },
                "Buyer": {
                    "BuyerName": self.buyer.name,
                    "BuyerPIN": self.buyer.pin,
                    "BuyerAddress": self.buyer.address
                },
                "Items": [
                    {
                        "ItemDescription": item.description,
                        "Quantity": item.quantity,
                        "UnitPrice": item.unit_price,
                        "VATRate": item.vat_rate,
                        "TotalExclusive": round(item.total_exclusive, 2),
                        "VATAmount": round(item.vat_amount, 2),
                        "TotalInclusive": round(item.total_inclusive, 2)
                    }
                    for item in self.items
                ],
                "Totals": {
                    "SubTotal": round(self.subtotal, 2),
                    "TotalVAT": round(self.total_vat, 2),
                    "GrandTotal": round(self.grand_total, 2)
                }
            }
        }
    
    def to_xml(self) -> str:
        """Convert to KRA ETIMS XML format"""
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Invoice>
    <Header>
        <InvoiceNumber>{self.invoice_number}</InvoiceNumber>
        <InvoiceDate>{self.date}</InvoiceDate>
        <InvoiceType>{self.invoice_type.upper()}</InvoiceType>
        <Currency>KES</Currency>
    </Header>
    <Seller>
        <Name>{self.seller.name}</Name>
        <PIN>{self.seller.pin}</PIN>
        <Address>{self.seller.address}</Address>
        <Phone>{self.seller.phone}</Phone>
        <Email>{self.seller.email}</Email>
    </Seller>
    <Buyer>
        <Name>{self.buyer.name}</Name>
        <PIN>{self.buyer.pin}</PIN>
        <Address>{self.buyer.address}</Address>
    </Buyer>
    <Items>'''
        for item in self.items:
            xml += f'''
        <Item>
            <Description>{item.description}</Description>
            <Quantity>{item.quantity}</Quantity>
            <UnitPrice>{item.unit_price}</UnitPrice>
            <VATRate>{item.vat_rate}</VATRate>
            <TotalExclusive>{round(item.total_exclusive, 2)}</TotalExclusive>
            <VATAmount>{round(item.vat_amount, 2)}</VATAmount>
            <TotalInclusive>{round(item.total_inclusive, 2)}</TotalInclusive>
        </Item>'''
        xml += f'''
    </Items>
    <Totals>
        <SubTotal>{round(self.subtotal, 2)}</SubTotal>
        <TotalVAT>{round(self.total_vat, 2)}</TotalVAT>
        <GrandTotal>{round(self.grand_total, 2)}</GrandTotal>
    </Totals>
</Invoice>'''
        return xml


def create_standard_invoice(
    seller_name: str, seller_pin: str, seller_address: str, seller_phone: str,
    buyer_name: str, buyer_pin: str, buyer_address: str,
    items: List[dict]
) -> ETIMSInvoice:
    """Helper to create a standard invoice"""
    seller = Party(seller_name, seller_pin, seller_address, seller_phone)
    buyer = Party(buyer_name, buyer_pin, buyer_address, "")
    
    invoice_items = [
        InvoiceItem(
            description=item["description"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            vat_rate=item.get("vat_rate", 16.0)
        )
        for item in items
    ]
    
    return ETIMSInvoice(
        invoice_number="",
        date=datetime.now().strftime("%Y-%m-%d"),
        seller=seller,
        buyer=buyer,
        items=invoice_items,
        invoice_type="standard"
    )


# Example usage
if __name__ == "__main__":
    # Example: Create an invoice for a sale
    invoice = create_standard_invoice(
        seller_name="Green Garnet Studios Ltd",
        seller_pin="P051234567A",
        seller_address="Nairobi, Kenya",
        seller_phone="+254700000000",
        buyer_name="Acme Corp Ltd",
        buyer_pin="P098765432B",
        buyer_address="Mombasa, Kenya",
        items=[
            {"description": "Video Production Services", "quantity": 1, "unit_price": 50000, "vat_rate": 16},
            {"description": "Post-Production Editing", "quantity": 1, "unit_price": 25000, "vat_rate": 16}
        ]
    )
    
    print("=" * 50)
    print("ETIMS INVOICE GENERATED")
    print("=" * 50)
    print(f"Invoice Number: {invoice.invoice_number}")
    print(f"Date: {invoice.date}")
    print(f"Seller: {invoice.seller.name} ({invoice.seller.pin})")
    print(f"Buyer: {invoice.buyer.name} ({invoice.buyer.pin})")
    print(f"Items: {len(invoice.items)}")
    print(f"Subtotal: KES {invoice.subtotal:,.2f}")
    print(f"VAT (16%): KES {invoice.total_vat:,.2f}")
    print(f"Grand Total: KES {invoice.grand_total:,.2f}")
    print("=" * 50)
    
    # Export to JSON
    print("\n--- JSON Export ---")
    print(json.dumps(invoice.to_kra_json(), indent=2))
    
    # Export to XML
    print("\n--- XML Export ---")
    print(invoice.to_xml())