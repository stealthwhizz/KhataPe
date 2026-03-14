"""Natural Language Payment Parser for KhataPe

Uses OpenAI GPT-4o to extract payment amount and payer name from text messages.
"""

import os
import json
import asyncio
from typing import Optional, Dict
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

# Load environment variables
load_dotenv()

EMERGENT_LLM_KEY = os.getenv('EMERGENT_LLM_KEY')


async def parse_text_message_async(text: str) -> Optional[Dict]:
    """
    Parse natural language text to extract payment amount and payer name.
    
    Args:
        text: Natural language message (e.g., "received 11800 from Rahul sharma")
    
    Returns:
        Dict with 'amount' (float) and 'payer' (string), or None if cannot parse
    """
    try:
        # Initialize LLM Chat with GPT-4o
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id="payment-parser",
            system_message="""You are a payment information extractor. Extract the amount (as a number) and payer name from payment messages.
Return ONLY a valid JSON object with 'amount' (float) and 'payer' (string) fields.
If you cannot extract both fields, return {"error": "Cannot parse"}.

Examples:
Input: "received 11800 from Rahul sharma"
Output: {"amount": 11800, "payer": "Rahul Sharma"}

Input: "got 5000 payment from abc traders"
Output: {"amount": 5000, "payer": "ABC Traders"}

Input: "hello how are you"
Output: {"error": "Cannot parse"}"""
        ).with_model("openai", "gpt-4o")
        
        # Create user message
        user_message = UserMessage(text=text)
        
        # Get response
        response = await chat.send_message(user_message)
        
        # Parse JSON response
        result = json.loads(response)
        
        # Check if parsing was successful
        if 'error' in result:
            print(f"⚠️  Could not parse message: {text}")
            return None
        
        # Validate required fields
        if 'amount' in result and 'payer' in result:
            print(f"✅ Parsed: Amount=₹{result['amount']}, Payer={result['payer']}")
            return {
                'amount': float(result['amount']),
                'payer': str(result['payer'])
            }
        else:
            print(f"⚠️  Invalid response format: {result}")
            return None
            
    except Exception as e:
        print(f"❌ Parsing error: {str(e)}")
        return None


def parse_text_message(text: str) -> Optional[Dict]:
    """
    Synchronous wrapper for parse_text_message_async.
    
    Args:
        text: Natural language message
    
    Returns:
        Dict with 'amount' and 'payer', or None if cannot parse
    """
    try:
        # Create new event loop if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run async function
        return loop.run_until_complete(parse_text_message_async(text))
    except Exception as e:
        print(f"❌ Error in sync wrapper: {str(e)}")
        return None


if __name__ == "__main__":
    # Test the parser
    test_messages = [
        "received 11800 from Rahul sharma",
        "got 5000 payment from abc traders",
        "payment of 25000 received from Priya Industries",
        "hello how are you"  # Should fail to parse
    ]
    
    print("Testing Payment Parser...\n")
    for msg in test_messages:
        print(f"\nInput: {msg}")
        result = parse_text_message(msg)
        print(f"Result: {result}")
        print("-" * 50)
