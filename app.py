# KenyaComply Web App
# Flask app for Kenyan Business Compliance
# Deployable to Vercel

from flask import Flask, render_template_string, request, jsonify
import json
from datetime import datetime

app = Flask(__name__)

# Import our modules
from etims_invoice import create_standard_invoice
from tax_calculator import calculate_paye, calculate_vat

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KenyaComply - Business Compliance Simplified</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 40px 20px; text-align: center; border-radius: 10px; margin-bottom: 30px; }
        h1 { font-size: 2.5rem; margin-bottom: 10px; }
        .subtitle { opacity: 0.8; font-size: 1.1rem; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .tab { padding: 12px 24px; background: white; border: none; border-radius: 8px; cursor: pointer; font-size: 1rem; transition: all 0.3s; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .tab:hover { transform: translateY(-2px); }
        .tab.active { background: #1a1a2e; color: white; }
        .card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: 600; }
        input, select, textarea { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 1rem; transition: border-color 0.3s; }
        input:focus, select:focus, textarea:focus { outline: none; border-color: #1a1a2e; }
        .row { display: flex; gap: 15px; flex-wrap: wrap; }
        .col { flex: 1; min-width: 200px; }
        button.primary { background: #1a1a2e; color: white; padding: 15px 30px; border: none; border-radius: 8px; font-size: 1.1rem; cursor: pointer; width: 100%; transition: all 0.3s; }
        button.primary:hover { background: #16213e; transform: translateY(-2px); }
        .result { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #1a1a2e; }
        .result h3 { margin-bottom: 15px; color: #1a1a2e; }
        .result-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e0e0e0; }
        .result-row:last-child { border-bottom: none; font-weight: bold; font-size: 1.2rem; }
        .badge { display: inline-block; background: #e8f5e9; color: #2e7d32; padding: 5px 12px; border-radius: 20px; font-size: 0.85rem; margin-right: 5px; }
        footer { text-align: center; padding: 20px; opacity: 0.7; font-size: 0.9rem; }
        .hidden { display: none; }
        @media (max-width: 600px) { .container { padding: 10px; } .card { padding: 20px; } h1 { font-size: 1.8rem; } }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏢 KenyaComply</h1>
            <p class="subtitle">Kenyan Business Compliance, Simplified</p>
            <div style="margin-top: 15px;">
                <span class="badge">ETIMS Invoices</span>
                <span class="badge">Tax Calculator</span>
                <span class="badge">KRA Compliant</span>
            </div>
        </header>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('invoice')">📄 Generate Invoice</button>
            <button class="tab" onclick="showTab('paye')">💰 PAYE Calculator</button>
            <button class="tab" onclick="showTab('vat')">🧾 VAT Calculator</button>
        </div>
        
        <!-- Invoice Form -->
        <div id="invoice" class="card">
            <h2>Generate ETIMS Invoice</h2>
            <form id="invoiceForm">
                <div class="row">
                    <div class="col form-group">
                        <label>Seller Name</label>
                        <input type="text" name="seller_name" placeholder="Your Company Ltd" required>
                    </div>
                    <div class="col form-group">
                        <label>Seller KRA PIN</label>
                        <input type="text" name="seller_pin" placeholder="P051234567A" required>
                    </div>
                </div>
                <div class="row">
                    <div class="col form-group">
                        <label>Buyer Name</label>
                        <input type="text" name="buyer_name" placeholder="Client Company Ltd" required>
                    </div>
                    <div class="col form-group">
                        <label>Buyer KRA PIN</label>
                        <input type="text" name="buyer_pin" placeholder="P098765432B" required>
                    </div>
                </div>
                <div class="form-group">
                    <label>Amount (KES)</label>
                    <input type="number" name="amount" placeholder="50000" required>
                </div>
                <button type="submit" class="primary">Generate Invoice</button>
            </form>
            <div id="invoiceResult" class="result hidden"></div>
        </div>
        
        <!-- PAYE Form -->
        <div id="paye" class="card hidden">
            <h2>Calculate PAYE Tax</h2>
            <form id="payeForm">
                <div class="form-group">
                    <label>Gross Monthly Salary (KES)</label>
                    <input type="number" name="salary" placeholder="250000" required>
                </div>
                <button type="submit" class="primary">Calculate PAYE</button>
            </form>
            <div id="payeResult" class="result hidden"></div>
        </div>
        
        <!-- VAT Form -->
        <div id="vat" class="card hidden">
            <h2>Calculate VAT</h2>
            <form id="vatForm">
                <div class="form-group">
                    <label>Output Sales (KES)</label>
                    <input type="number" name="sales" placeholder="100000" required>
                </div>
                <div class="row">
                    <div class="col form-group">
                        <label>Exempt Sales (KES)</label>
                        <input type="number" name="exempt" placeholder="0">
                    </div>
                    <div class="col form-group">
                        <label>Input VAT (KES)</label>
                        <input type="number" name="input_vat" placeholder="0">
                    </div>
                </div>
                <button type="submit" class="primary">Calculate VAT</button>
            </form>
            <div id="vatResult" class="result hidden"></div>
        </div>
        
        <footer>
            <p>Built by Mwakulomba 🎥📜 | KenyaComply v1.0</p>
        </footer>
    </div>
    
    <script>
        function showTab(tabId) {
            document.querySelectorAll('.card').forEach(c => c.classList.add('hidden'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById(tabId).classList.remove('hidden');
            event.target.classList.add('active');
        }
        
        // Invoice Form
        document.getElementById('invoiceForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            data.amount = parseFloat(data.amount);
            
            const response = await fetch('/api/invoice', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await response.json();
            
            document.getElementById('invoiceResult').innerHTML = `
                <h3>✅ Invoice Generated</h3>
                <div class="result-row"><span>Invoice Number</span><span>${result.invoice_number}</span></div>
                <div class="result-row"><span>Date</span><span>${result.date}</span></div>
                <div class="result-row"><span>Subtotal</span><span>KES ${result.subtotal.toLocaleString()}</span></div>
                <div class="result-row"><span>VAT (16%)</span><span>KES ${result.vat.toLocaleString()}</span></div>
                <div class="result-row"><span>Grand Total</span><span>KES ${result.total.toLocaleString()}</span></div>
            `;
            document.getElementById('invoiceResult').classList.remove('hidden');
        });
        
        // PAYE Form
        document.getElementById('payeForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = {salary: parseFloat(formData.get('salary'))};
            
            const response = await fetch('/api/paye', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await response.json();
            
            document.getElementById('payeResult').innerHTML = `
                <h3>✅ PAYE Calculated</h3>
                <div class="result-row"><span>Gross Salary</span><span>KES ${result.gross_salary.toLocaleString()}</span></div>
                <div class="result-row"><span>NSSF</span><span>KES ${result.nssf.toLocaleString()}</span></div>
                <div class="result-row"><span>Taxable Income</span><span>KES ${result.taxable_income.toLocaleString()}</span></div>
                <div class="result-row"><span>Tax (after relief)</span><span>KES ${result.tax_after_relief.toLocaleString()}</span></div>
                <div class="result-row"><span>NHIF</span><span>KES ${result.nhif.toLocaleString()}</span></div>
                <div class="result-row"><span>NET SALARY</span><span>KES ${result.net_salary.toLocaleString()}</span></div>
            `;
            document.getElementById('payeResult').classList.remove('hidden');
        });
        
        // VAT Form
        document.getElementById('vatForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = {
                sales: parseFloat(formData.get('sales')),
                exempt: parseFloat(formData.get('exempt') || 0),
                input_vat: parseFloat(formData.get('input_vat') || 0)
            };
            
            const response = await fetch('/api/vat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await response.json();
            
            document.getElementById('vatResult').innerHTML = `
                <h3>✅ VAT Calculated</h3>
                <div class="result-row"><span>Output Sales</span><span>KES ${result.gross_sales.toLocaleString()}</span></div>
                <div class="result-row"><span>Exempt Sales</span><span>KES ${result.vat_exempt.toLocaleString()}</span></div>
                <div class="result-row"><span>VAT Collected</span><span>KES ${result.vat_collected.toLocaleString()}</span></div>
                <div class="result-row"><span>Input VAT</span><span>KES ${result.input_vat.toLocaleString()}</span></div>
                <div class="result-row"><span>NET VAT PAYABLE</span><span>KES ${result.net_vat_payable.toLocaleString()}</span></div>
            `;
            document.getElementById('vatResult').classList.remove('hidden');
        });
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/invoice", methods=["POST"])
def api_invoice():
    data = request.json
    invoice = create_standard_invoice(
        seller_name=data["seller_name"],
        seller_pin=data["seller_pin"],
        seller_address="Nairobi, Kenya",
        seller_phone="+254700000000",
        buyer_name=data["buyer_name"],
        buyer_pin=data["buyer_pin"],
        buyer_address="Kenya",
        items=[{"description": "Service", "quantity": 1, "unit_price": data["amount"], "vat_rate": 16}]
    )
    return jsonify({
        "invoice_number": invoice.invoice_number,
        "date": invoice.date,
        "subtotal": invoice.subtotal,
        "vat": invoice.total_vat,
        "total": invoice.grand_total
    })

@app.route("/api/paye", methods=["POST"])
def api_paye():
    data = request.json
    result = calculate_paye(data["salary"])
    return jsonify(result.to_dict())

@app.route("/api/vat", methods=["POST"])
def api_vat():
    data = request.json
    result = calculate_vat(data["sales"], data.get("exempt", 0), data.get("input_vat", 0))
    return jsonify({
        "gross_sales": result.gross_sales,
        "vat_exempt": result.vat_exempt,
        "vat_collected": result.vat_collected,
        "input_vat": result.input_vat,
        "net_vat_payable": result.net_vat_payable
    })

@app.route("/health")
def health():
    return {"status": "ok", "service": "kenya-comply"}

# Vercel handler
app.debug = True
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
