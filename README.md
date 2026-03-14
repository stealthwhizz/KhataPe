# 🧾 KhataPe - WhatsApp CFO Agent for Indian SMBs

**Har payment ka hisaab. WhatsApp pe**

KhataPe is an automated financial assistant that handles payment tracking, GST calculations, and WhatsApp notifications for Indian small and medium businesses.

## 🌟 Features

- **Automated GST Calculation**: Automatically calculates 18% GST with CGST and SGST breakdown
- **Razorpay Integration**: Receives payment webhooks and processes them automatically
- **WhatsApp AI Parser**: Uses OpenAI GPT-4o to parse natural language payment messages
- **Transaction Ledger**: SQLite database for persistent transaction storage
- **Monthly Reporting**: Real-time monthly total calculations
- **WhatsApp Notifications**: Sends detailed payment summaries via Twilio WhatsApp

## 🏗️ Architecture

```
KhataPe/
├── main.py           # FastAPI application with webhook endpoints
├── gst.py            # GST calculation engine (18% with CGST/SGST split)
├── ledger.py         # SQLite transaction database
├── whatsapp.py       # Twilio WhatsApp messaging
├── parser.py         # OpenAI GPT-4o natural language parser
├── .env              # Environment configuration
├── .env.example      # Environment template
├── requirements.txt  # Python dependencies
└── khatape.db        # SQLite database (auto-created)
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
# OpenAI Integration (Emergent LLM Key provided)
EMERGENT_LLM_KEY=sk-emergent-20cAf19B1B060318b5

# Razorpay Credentials
RAZORPAY_KEY=your_razorpay_key_here
RAZORPAY_SECRET=your_razorpay_secret_here

# Twilio WhatsApp Integration
TWILIO_SID=your_twilio_account_sid
TWILIO_AUTH=your_twilio_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Merchant WhatsApp Number
MERCHANT_WHATSAPP=whatsapp:+919999999999
```

### 3. Run the Server

```bash
# Development
python main.py

# Production (with supervisor)
supervisorctl start khatape
```

Server runs on: `http://0.0.0.0:8000`

## 📡 API Endpoints

### Root Endpoint
```bash
GET /
```
Returns API information and available endpoints.

### Health Check
```bash
GET /health
```
Returns server health status.

### Get All Transactions
```bash
GET /transactions
```
Returns all transactions with monthly total.

**Response:**
```json
{
  "transactions": [
    {
      "id": 1,
      "timestamp": "2026-03-14T08:20:11.964452",
      "payer": "Rahul Sharma",
      "amount": 11800.0,
      "gst": 1800.0,
      "cgst": 900.0,
      "sgst": 900.0,
      "net": 10000.0
    }
  ],
  "monthly_total": 10000.0,
  "count": 1
}
```

### Razorpay Webhook
```bash
POST /webhook/razorpay
```

Handles `payment.captured` webhook from Razorpay.

**Example Payload:**
```json
{
  "event": "payment.captured",
  "payload": {
    "payment": {
      "entity": {
        "amount": 1180000,
        "email": "customer@example.com",
        "contact": "+919999999999"
      }
    }
  }
}
```

**Response:**
```json
{
  "status": "ok",
  "transaction_id": 1
}
```

### WhatsApp Webhook
```bash
POST /webhook/whatsapp
```

Handles incoming WhatsApp messages from Twilio.

**Example:**
```bash
curl -X POST http://localhost:8000/webhook/whatsapp \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "Body=received 11800 from Rahul sharma&From=whatsapp:+919999999999"
```

## 💡 Usage Examples

### Test GST Calculation
```bash
python gst.py
```

### Test Ledger Operations
```bash
python ledger.py
```

### Test WhatsApp Messaging
```bash
python whatsapp.py
```

### Test Natural Language Parser
```bash
python parser.py
```

### Test Razorpay Webhook
```bash
curl -X POST http://localhost:8000/webhook/razorpay \
  -H "Content-Type: application/json" \
  -d '{
    "event": "payment.captured",
    "payload": {
      "payment": {
        "entity": {
          "amount": 2360000,
          "email": "customer@example.com"
        }
      }
    }
  }'
```

## 📊 GST Calculation Logic

KhataPe uses tax-inclusive GST calculation:

- **GST Rate**: 18%
- **Formula**: `gst = amount × 18/118`
- **CGST**: GST ÷ 2 (9%)
- **SGST**: GST ÷ 2 (9%)
- **Net Income**: Gross Amount - GST

**Example:**
```
Gross Amount: ₹11,800
GST (18%): ₹1,800
CGST (9%): ₹900
SGST (9%): ₹900
Net Income: ₹10,000
```

## 🤖 Natural Language Processing

The system uses OpenAI GPT-4o to parse payment messages:

**Supported Formats:**
- "received 11800 from Rahul sharma"
- "got 5000 payment from abc traders"
- "payment of 25000 received from Priya Industries"

**Extracted Data:**
- Amount (float)
- Payer name (string)

## 📱 WhatsApp Message Format

```
✅ Payment received!
From: Rahul Sharma
Gross: ₹11,800.00
GST (18%): ₹1,800.00 (CGST ₹900.00 + SGST ₹900.00)
Net Income: ₹10,000.00

📊 March Total: ₹10,000.00
🟢 GST Health: 94/100

Powered by KhataPe 🧾
```

## 🔐 Security Notes

- Never commit `.env` file to version control
- Use environment variables for all sensitive data
- Validate webhook signatures in production
- Use HTTPS in production environment

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLite
- **AI/ML**: OpenAI GPT-4o (via Emergent LLM Key)
- **Messaging**: Twilio WhatsApp API
- **Payment**: Razorpay Webhooks

## 📝 Module Details

### gst.py
Calculates GST breakdown with 18% rate split into CGST and SGST.

### ledger.py
SQLite-based transaction logging with monthly aggregation.

### whatsapp.py
Twilio integration for sending WhatsApp messages.

### parser.py
OpenAI GPT-4o integration for parsing natural language payment messages.

### main.py
FastAPI application with webhook endpoints for Razorpay and WhatsApp.

## 🧪 Testing

All modules include built-in tests. Run individual modules to test:

```bash
python gst.py         # Test GST calculations
python ledger.py      # Test database operations
python whatsapp.py    # Test WhatsApp messaging
python parser.py      # Test NLP parser
```

## 📦 Dependencies

- fastapi==0.115.0
- uvicorn==0.32.0
- python-dotenv==1.0.1
- twilio==9.3.7
- requests==2.32.3
- emergentintegrations
- sqlalchemy==2.0.36

## 🤝 Support

For issues or questions, please contact the development team.

## 📄 License

MIT License - Copyright (c) 2026 Amogh Sunil

---

**Built with ❤️ for Indian SMBs**
=======
# Here are your Instructions
>>>>>>> origin/S2.dev-live-streaming
