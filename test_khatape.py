#!/usr/bin/env python
"""
Test script for KhataPe backend
Runs comprehensive tests on all endpoints and modules
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def test_health_check():
    """Test health check endpoint"""
    print_header("Testing Health Check")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print("✅ Health check passed")

def test_root_endpoint():
    """Test root endpoint"""
    print_header("Testing Root Endpoint")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    assert response.json()["app"] == "KhataPe"
    print("✅ Root endpoint passed")

def test_get_transactions():
    """Test get transactions endpoint"""
    print_header("Testing Get Transactions")
    response = requests.get(f"{BASE_URL}/transactions")
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Total Transactions: {data['count']}")
    print(f"Monthly Total: ₹{data['monthly_total']}")
    print(f"Response: {json.dumps(data, indent=2)}")
    assert response.status_code == 200
    print("✅ Get transactions passed")
    return data['count']

def test_razorpay_webhook():
    """Test Razorpay webhook endpoint"""
    print_header("Testing Razorpay Webhook")
    
    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "amount": 5900000,  # ₹59,000 in paise
                    "email": "test@khatape.com",
                    "contact": "+919876543210"
                }
            }
        }
    }
    
    print(f"Sending payload: {json.dumps(payload, indent=2)}")
    response = requests.post(
        f"{BASE_URL}/webhook/razorpay",
        json=payload
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    print("✅ Razorpay webhook passed")
    
    # Wait for processing
    time.sleep(1)

def test_whatsapp_webhook():
    """Test WhatsApp webhook endpoint"""
    print_header("Testing WhatsApp Webhook")
    
    data = {
        "Body": "received 35400 from Mumbai Enterprises",
        "From": "whatsapp:+919123456789"
    }
    
    print(f"Sending WhatsApp message: {data['Body']}")
    response = requests.post(
        f"{BASE_URL}/webhook/whatsapp",
        data=data
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:100]}...")
    assert response.status_code == 200
    print("✅ WhatsApp webhook passed")
    
    # Wait for processing
    time.sleep(2)

def test_whatsapp_invalid_message():
    """Test WhatsApp webhook with invalid message"""
    print_header("Testing WhatsApp Webhook - Invalid Message")
    
    data = {
        "Body": "hello this is not a payment message",
        "From": "whatsapp:+919123456789"
    }
    
    print(f"Sending invalid message: {data['Body']}")
    response = requests.post(
        f"{BASE_URL}/webhook/whatsapp",
        data=data
    )
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200
    print("✅ Invalid message handled correctly")

def run_all_tests():
    """Run all tests"""
    print("\n" + "🧪 "*30)
    print("  KHATAPE BACKEND TEST SUITE")
    print("🧪 "*30)
    
    try:
        # Initial transaction count
        initial_count = test_get_transactions()
        
        # Run all tests
        test_health_check()
        test_root_endpoint()
        test_razorpay_webhook()
        test_whatsapp_webhook()
        test_whatsapp_invalid_message()
        
        # Final transaction count
        final_count = test_get_transactions()
        
        # Summary
        print_header("TEST SUMMARY")
        print(f"Initial Transactions: {initial_count}")
        print(f"Final Transactions: {final_count}")
        print(f"New Transactions Added: {final_count - initial_count}")
        print("\n✅ ALL TESTS PASSED!")
        print("\n🎉 KhataPe backend is working perfectly!")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    run_all_tests()
