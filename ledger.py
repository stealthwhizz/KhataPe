"""SQLite Ledger Module for KhataPe

Manages transaction logging and retrieval using SQLite database.
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), 'khatape.db')


def _get_connection():
    """Get SQLite database connection and ensure table exists."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Create table if it doesn't exist
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            payer TEXT NOT NULL,
            amount REAL NOT NULL,
            gst REAL NOT NULL,
            cgst REAL NOT NULL,
            sgst REAL NOT NULL,
            net REAL NOT NULL
        )
    """)
    conn.commit()
    
    return conn


def log_transaction(payer: str, amount: float, gst: float, cgst: float, sgst: float, net: float) -> int:
    """
    Log a transaction to the database.
    
    Args:
        payer: Name of the payer
        amount: Gross amount
        gst: Total GST amount
        cgst: Central GST amount
        sgst: State GST amount
        net: Net income after GST
    
    Returns:
        int: ID of the inserted transaction
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO transactions (timestamp, payer, amount, gst, cgst, sgst, net)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, payer, amount, gst, cgst, sgst, net))
    
    conn.commit()
    transaction_id = cursor.lastrowid
    conn.close()
    
    print(f"✅ Transaction logged: ID={transaction_id}, Payer={payer}, Amount=₹{amount}")
    
    return transaction_id


def get_monthly_total() -> float:
    """
    Get the sum of net income for the current month.
    
    Returns:
        float: Total net income for current month
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Get current year and month
    current_month = datetime.now().strftime('%Y-%m')
    
    cursor.execute("""
        SELECT SUM(net) as total
        FROM transactions
        WHERE timestamp LIKE ?
    """, (f"{current_month}%",))
    
    result = cursor.fetchone()
    conn.close()
    
    total = result['total'] if result['total'] else 0.0
    return round(total, 2)


def get_all_transactions() -> List[Dict]:
    """
    Get all transactions from the database.
    
    Returns:
        List[Dict]: List of all transactions as dictionaries
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, timestamp, payer, amount, gst, cgst, sgst, net
        FROM transactions
        ORDER BY timestamp DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    transactions = [dict(row) for row in rows]
    return transactions


if __name__ == "__main__":
    # Test the ledger
    print("Testing Ledger Module...")
    
    # Log a test transaction
    transaction_id = log_transaction(
        payer="Rahul Sharma",
        amount=11800.00,
        gst=1800.00,
        cgst=900.00,
        sgst=900.00,
        net=10000.00
    )
    
    print(f"\nTransaction ID: {transaction_id}")
    print(f"Monthly Total: ₹{get_monthly_total()}")
    print(f"\nAll Transactions: {len(get_all_transactions())} records")
