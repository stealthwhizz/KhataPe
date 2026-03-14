"""WhatsApp Messaging Module for KhataPe

Handles sending WhatsApp messages via Twilio API.
"""

import os
from twilio.rest import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TWILIO_SID = os.getenv('TWILIO_SID')
TWILIO_AUTH = os.getenv('TWILIO_AUTH')
TWILIO_WHATSAPP_FROM = os.getenv('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')


def send_message(to_number: str, body: str) -> bool:
    """
    Send a WhatsApp message using Twilio.
    
    Args:
        to_number: Recipient's phone number (format: whatsapp:+91XXXXXXXXXX)
        body: Message content
    
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    try:
        # Check if Twilio credentials are configured
        if not TWILIO_SID or not TWILIO_AUTH or TWILIO_SID == 'twilio_sid_placeholder':
            print("⚠️  Twilio credentials not configured. Skipping WhatsApp message.")
            print(f"📱 Would send to {to_number}:")
            print(f"{body}")
            print("-" * 50)
            return False
        
        # Format phone number if needed
        if not to_number.startswith('whatsapp:'):
            to_number = f"whatsapp:{to_number}"
        
        # Initialize Twilio client
        client = Client(TWILIO_SID, TWILIO_AUTH)
        
        # Send message
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            body=body,
            to=to_number
        )
        
        print(f"✅ WhatsApp message sent: SID={message.sid}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send WhatsApp message: {str(e)}")
        print(f"📱 Attempted to send to {to_number}:")
        print(f"{body}")
        print("-" * 50)
        return False


if __name__ == "__main__":
    # Test the WhatsApp module
    test_message = """✅ Payment received!
From: Test User
Gross: ₹11800.00
GST (18%): ₹1800.00 (CGST ₹900.00 + SGST ₹900.00)
Net Income: ₹10000.00

📊 March Total: ₹10000.00
🟢 GST Health: 94/100

Powered by KhataPe 🧾"""
    
    send_message("whatsapp:+919999999999", test_message)
