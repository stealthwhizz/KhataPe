"""GST Calculation Module for KhataPe

Handles 18% GST calculation with CGST and SGST split for intra-state transactions.
"""

def calculate(amount: float) -> dict:
    """
    Calculate GST breakdown from gross amount (tax-inclusive).
    
    Args:
        amount: Gross amount in rupees (including GST)
    
    Returns:
        dict: {
            'gross': Gross amount,
            'gst': Total GST amount,
            'cgst': Central GST (9%),
            'sgst': State GST (9%),
            'net': Net income after GST
        }
    """
    # GST is 18% of the gross amount (tax-inclusive calculation)
    # Formula: GST = amount * 18/118
    gst = round(amount * 18 / 118, 2)
    
    # Split GST equally into CGST and SGST (9% each)
    cgst = round(gst / 2, 2)
    sgst = round(gst / 2, 2)
    
    # Net income = Gross - GST
    net = round(amount - gst, 2)
    
    return {
        'gross': round(amount, 2),
        'gst': gst,
        'cgst': cgst,
        'sgst': sgst,
        'net': net
    }


if __name__ == "__main__":
    # Test the GST calculation
    test_amount = 11800
    result = calculate(test_amount)
    print(f"GST Calculation for ₹{test_amount}:")
    print(f"Gross: ₹{result['gross']}")
    print(f"GST (18%): ₹{result['gst']}")
    print(f"CGST (9%): ₹{result['cgst']}")
    print(f"SGST (9%): ₹{result['sgst']}")
    print(f"Net Income: ₹{result['net']}")
