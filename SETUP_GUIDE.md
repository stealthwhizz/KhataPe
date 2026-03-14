# KhataPe - Setup & Configuration Guide

## ✅ Installation Complete

KhataPe backend has been successfully installed and is running!

## 🚀 Service Status

**Server Running**: http://0.0.0.0:8000
**Service**: khatape (managed by supervisor)
**Database**: SQLite at /app/khatape.db

## 🔧 Manage Service

```bash
# Check status
supervisorctl status khatape

# Restart service
supervisorctl restart khatape

# Stop service
supervisorctl stop khatape

# Start service
supervisorctl start khatape

# View logs
tail -f /var/log/supervisor/khatape.out.log
tail -f /var/log/supervisor/khatape.err.log
```

## 📡 API Endpoints

### Available Endpoints
- `GET /` - API information
- `GET /health` - Health check
- `GET /transactions` - Get all transactions
- `POST /webhook/razorpay` - Razorpay payment webhook
- `POST /webhook/whatsapp` - Twilio WhatsApp webhook

### Test Commands

```bash
# Health check
curl http://localhost:8000/health

# Get all transactions
curl http://localhost:8000/transactions

# Test Razorpay webhook
curl -X POST http://localhost:8000/webhook/razorpay \
  -H "Content-Type: application/json" \
  -d '{
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
  }'

# Test WhatsApp webhook
curl -X POST http://localhost:8000/webhook/whatsapp \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "Body=received 11800 from Rahul sharma&From=whatsapp:+919999999999"
```

## 🔑 Current Configuration

### ✅ Configured
- **OpenAI GPT-4o**: Using Emergent LLM Key (sk-emergent-20cAf19B1B060318b5)
- **FastAPI Server**: Running on port 8000
- **SQLite Database**: khatape.db (auto-created)
- **GST Calculation**: 18% with CGST/SGST split

### ⚠️ Placeholders (To be configured for production)
- **Twilio Credentials**: TWILIO_SID, TWILIO_AUTH
- **Razorpay Credentials**: RAZORPAY_KEY, RAZORPAY_SECRET
- **Merchant WhatsApp**: MERCHANT_WHATSAPP

## 📝 Configuration File

Edit `/app/.env` to add your credentials:

```bash
# OpenAI Integration (Already configured)
EMERGENT_LLM_KEY=sk-emergent-20cAf19B1B060318b5

# Add your Razorpay credentials
RAZORPAY_KEY=your_razorpay_key_here
RAZORPAY_SECRET=your_razorpay_secret_here

# Add your Twilio credentials
TWILIO_SID=your_twilio_account_sid
TWILIO_AUTH=your_twilio_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Set your WhatsApp number
MERCHANT_WHATSAPP=whatsapp:+919999999999
```

After updating .env, restart the service:
```bash
supervisorctl restart khatape
```

## 🧪 Run Tests

```bash
# Run comprehensive test suite
python /app/test_khatape.py

# Test individual modules
python /app/gst.py          # Test GST calculations
python /app/ledger.py       # Test database operations
python /app/whatsapp.py     # Test WhatsApp messaging
python /app/parser.py       # Test NLP parser
```

## 📊 Database

**Location**: `/app/khatape.db`
**Type**: SQLite
**Schema**:
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    payer TEXT NOT NULL,
    amount REAL NOT NULL,
    gst REAL NOT NULL,
    cgst REAL NOT NULL,
    sgst REAL NOT NULL,
    net REAL NOT NULL
)
```

**View data**:
```bash
sqlite3 /app/khatape.db "SELECT * FROM transactions;"
```

## 🔗 Integration Setup

### 1. Razorpay Webhook Setup

1. Login to Razorpay Dashboard
2. Go to Settings → Webhooks
3. Add webhook URL: `https://your-domain.com/webhook/razorpay`
4. Select event: `payment.captured`
5. Save and test

### 2. Twilio WhatsApp Setup

1. Login to Twilio Console
2. Go to Messaging → Try it out → Send a WhatsApp message
3. Get your Account SID and Auth Token
4. Configure webhook URL: `https://your-domain.com/webhook/whatsapp`
5. Update .env with credentials

### 3. Testing Locally

Use ngrok to expose local server for webhook testing:
```bash
ngrok http 8000
```

Use the ngrok URL as your webhook endpoint.

## 📈 Features Working

✅ GST Calculation (18% with CGST/SGST split)
✅ SQLite Transaction Ledger
✅ Monthly Total Calculation
✅ Razorpay Webhook Processing
✅ WhatsApp Message Parsing (OpenAI GPT-4o)
✅ WhatsApp Notifications (Twilio)
✅ RESTful API Endpoints
✅ FastAPI with CORS Support
✅ Automatic Service Management (Supervisor)
✅ Comprehensive Error Handling

## 📚 Documentation

Full documentation available in `/app/README.md`

## 🆘 Troubleshooting

### Service not starting
```bash
# Check logs
tail -n 100 /var/log/supervisor/khatape.err.log

# Restart service
supervisorctl restart khatape
```

### Database issues
```bash
# Check database
ls -lh /app/khatape.db

# View records
python -c "import ledger; print(ledger.get_all_transactions())"
```

### API not responding
```bash
# Check if service is running
supervisorctl status khatape

# Check if port is open
netstat -tulpn | grep 8000

# Test health endpoint
curl http://localhost:8000/health
```

## 📞 Support

For issues or questions:
1. Check `/app/README.md` for detailed documentation
2. Review logs in `/var/log/supervisor/khatape.*.log`
3. Run test suite: `python /app/test_khatape.py`

---

**Status**: ✅ System Ready for Testing
**Next Steps**: Configure Twilio and Razorpay credentials for production use
