# KenyaComply 🏢
**AI Agent for Kenyan Business Compliance**

All-in-one tool for Kenyan businesses to:
- Generate KRA-compliant ETIMS e-invoices
- Calculate PAYE and VAT
- Accept M-Pesa payments
- Save invoices to the cloud

---

## Quick Start (Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py

# Open http://localhost:5000
```

---

## Tech Stack

| Category | Tool | Purpose |
|----------|------|---------|
| **Hosting** | Vercel | Deployment |
| **Auth** | Clerk | User authentication |
| **Database** | Supabase | Store invoices, user data |
| **Payments** | M-Pesa (Flutterwave) | Mobile money payments |
| **Analytics** | PostHog | Track usage |
| **Errors** | Sentry | Bug monitoring |

---

## Environment Variables

Create a `.env` file:

```env
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key

# Clerk
CLERK_PUBLISHABLE_KEY=your_clerk_key
CLERK_SECRET_KEY=your_clerk_secret

# Flutterwave (M-Pesa)
FLUTTERWAVE_PUBLIC_KEY=your_key
FLUTTERWAVE_SECRET_KEY=your_secret

# PostHog
POSTHOG_KEY=your_key

# Sentry
SENTRY_DSN=your_dsn
```

---

## Deployment to Vercel

### Option 1: GitHub
1. Push to GitHub
2. Go to [vercel.com](https://vercel.com)
3. Import project
4. Add environment variables in Vercel dashboard
5. Deploy

### Option 2: Vercel CLI
```bash
npm i -g vercel
cd kenya-comply
vercel
```

---

## Features

| Feature | Status |
|---------|--------|
| ETIMS Invoice Generator | ✅ Working |
| PAYE Calculator | ✅ Working |
| VAT Calculator | ✅ Working |
| User Authentication (Clerk) | 🔄 Coming Soon |
| Save to Supabase | 🔄 Coming Soon |
| M-Pesa Payments | 🔄 Coming Soon |
| Web Interface | ✅ Working |

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web UI |
| `/api/invoice` | POST | Generate invoice |
| `/api/paye` | POST | Calculate PAYE |
| `/api/vat` | POST | Calculate VAT |
| `/api/save-invoice` | POST | Save to Supabase |
| `/api/payments/mpesa` | POST | Initiate M-Pesa payment |
| `/health` | GET | Health check |

---

## Supabase Schema

```sql
-- Users table (extends Clerk)
create table users (
  id text primary key,
  email text,
  name text,
  created_at timestamptz default now()
);

-- Invoices table
create table invoices (
  id text primary key,
  user_id text references users(id),
  invoice_number text,
  seller_name text,
  seller_pin text,
  buyer_name text,
  buyer_pin text,
  amount decimal,
  status text default 'draft',
  created_at timestamptz default now()
);

-- Payments table
create table payments (
  id text primary key,
  user_id text references users(id),
  invoice_id text references invoices(id),
  amount decimal,
  phone text,
  status text default 'pending',
  mpesa_transaction_id text,
  created_at timestamptz default now()
);
```

---

## M-Pesa Integration (Flutterwave)

### Payment Flow
1. User clicks "Pay with M-Pesa"
2. Enter phone number
3. Flutterwave sends STK push
4. User approves on phone
5. Webhook confirms payment
6. Invoice marked as paid

---

## Next Steps

1. [x] Deploy basic version
2. [ ] Add Clerk authentication
3. [ ] Add Supabase database
4. [ ] Add M-Pesa payments
5. [ ] Add PostHog analytics

---

## License

MIT License - Use freely for your business.

---

**Built by Mwakulomba** 🎥📜
