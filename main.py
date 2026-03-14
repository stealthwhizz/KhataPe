"""KhataPe - WhatsApp CFO Agent for Indian SMBs

FastAPI backend for handling Razorpay payment webhooks and WhatsApp messages.
"""

import os
from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, Request, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from dotenv import load_dotenv

import gst
import ledger
import whatsapp
import parser

# Load environment variables
load_dotenv()

MERCHANT_WHATSAPP = os.getenv('MERCHANT_WHATSAPP', 'whatsapp:+919999999999')

# Initialize FastAPI app
app = FastAPI(
    title="KhataPe",
    description="WhatsApp CFO Agent for Indian SMBs",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def format_currency(amount: float) -> str:
    """Format currency in Indian style."""
    return f"₹{amount:,.2f}"


def create_whatsapp_message(payer: str, gst_data: Dict, monthly_total: float) -> str:
    """
    Create formatted WhatsApp message with payment details.
    
    Args:
        payer: Name of the payer
        gst_data: GST calculation dict from gst.calculate()
        monthly_total: Current month's total net income
    
    Returns:
        str: Formatted WhatsApp message
    """
    current_month = datetime.now().strftime('%B')
    
    message = f"""✅ Payment received!
From: {payer}
Gross: {format_currency(gst_data['gross'])}
GST (18%): {format_currency(gst_data['gst'])} (CGST {format_currency(gst_data['cgst'])} + SGST {format_currency(gst_data['sgst'])})
Net Income: {format_currency(gst_data['net'])}

📊 {current_month} Total: {format_currency(monthly_total)}
🟢 GST Health: 94/100

Powered by KhataPe 🧾"""
    
    return message


def process_payment(amount: float, payer: str) -> Dict[str, Any]:
    """
    Process a payment: calculate GST, log to ledger, send WhatsApp.
    
    Args:
        amount: Payment amount in rupees
        payer: Name of the payer
    
    Returns:
        Dict with processing results
    """
    # Calculate GST
    gst_data = gst.calculate(amount)
    
    # Log to ledger
    transaction_id = ledger.log_transaction(
        payer=payer,
        amount=gst_data['gross'],
        gst=gst_data['gst'],
        cgst=gst_data['cgst'],
        sgst=gst_data['sgst'],
        net=gst_data['net']
    )
    
    # Get monthly total
    monthly_total = ledger.get_monthly_total()
    
    # Create and send WhatsApp message
    message = create_whatsapp_message(payer, gst_data, monthly_total)
    whatsapp.send_message(MERCHANT_WHATSAPP, message)
    
    return {
        'transaction_id': transaction_id,
        'gst_data': gst_data,
        'monthly_total': monthly_total,
        'message_sent': True
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": "KhataPe",
        "description": "WhatsApp CFO Agent for Indian SMBs",
        "version": "1.0.0",
        "endpoints": [
            "POST /webhook/razorpay - Razorpay payment webhook",
            "POST /webhook/whatsapp - Twilio WhatsApp webhook",
            "GET /transactions - Get all transactions"
        ]
    }


@app.post("/webhook/razorpay")
async def razorpay_webhook(request: Request):
    """
    Handle Razorpay payment.captured webhook.
    
    Expected payload:
    {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "amount": 1180000,  // in paise
                    "email": "customer@example.com",
                    "contact": "+919999999999"
                }
            }
        }
    }
    """
    try:
        # Parse request body
        payload = await request.json()
        print(f"🔔 Razorpay webhook received: {payload.get('event')}")
        
        # Extract payment data
        payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
        
        # Amount is in paise, convert to rupees
        amount_paise = payment_entity.get('amount', 0)
        amount = amount_paise / 100
        
        # Extract payer info (email, contact, or default)
        payer = payment_entity.get('email') or payment_entity.get('contact') or "Customer"
        
        print(f"💵 Processing payment: ₹{amount} from {payer}")
        
        # Process payment
        result = process_payment(amount, payer)
        
        print(f"✅ Payment processed successfully: Transaction ID={result['transaction_id']}")
        
        return JSONResponse(content={"status": "ok", "transaction_id": result['transaction_id']})
        
    except Exception as e:
        print(f"❌ Error processing Razorpay webhook: {str(e)}")
        # Return 200 to Razorpay even on error to avoid retries
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=200)


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
    """
    Handle incoming WhatsApp messages from Twilio.
    
    Twilio sends form data with:
    - Body: The message text
    - From: Sender's WhatsApp number (format: whatsapp:+919999999999)
    """
    try:
        print(f"📱 WhatsApp message received from {From}: {Body}")
        
        # Parse message to extract amount and payer (use async version directly)
        parsed = await parser.parse_text_message_async(Body)
        
        if parsed and 'amount' in parsed and 'payer' in parsed:
            amount = parsed['amount']
            payer = parsed['payer']
            
            print(f"💵 Processing WhatsApp payment: ₹{amount} from {payer}")
            
            # Process payment
            result = process_payment(amount, payer)
            
            # Send reply to sender
            gst_data = result['gst_data']
            monthly_total = result['monthly_total']
            reply_message = create_whatsapp_message(payer, gst_data, monthly_total)
            whatsapp.send_message(From, reply_message)
            
            print(f"✅ WhatsApp payment processed: Transaction ID={result['transaction_id']}")
            
            # Return TwiML response
            return PlainTextResponse(content="<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>", media_type="text/xml")
        else:
            print("⚠️  Could not parse payment information from message")
            
            # Send help message
            help_message = "🧾 KhataPe: Please send payment info in format: 'received [amount] from [payer name]'"
            whatsapp.send_message(From, help_message)
            
            return PlainTextResponse(content="<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>", media_type="text/xml")
            
    except Exception as e:
        print(f"❌ Error processing WhatsApp webhook: {str(e)}")
        return PlainTextResponse(content="<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response></Response>", media_type="text/xml")


@app.get("/transactions")
async def get_transactions():
    """
    Get all transactions from the ledger.
    
    Returns:
        List of all transactions with full details
    """
    try:
        transactions = ledger.get_all_transactions()
        monthly_total = ledger.get_monthly_total()
        
        return JSONResponse(content={
            "transactions": transactions,
            "monthly_total": monthly_total,
            "count": len(transactions)
        })
        
    except Exception as e:
        print(f"❌ Error fetching transactions: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": "KhataPe"}


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting KhataPe server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
