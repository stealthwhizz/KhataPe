from fastapi import FastAPI, APIRouter, Form, HTTPException, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
import json
import hmac
import hashlib
import requests
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Dict, List, Optional
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")
S2_STREAM = "transactions"


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_invoice_image(image_url: str) -> dict:
    unsiloed_key = os.getenv("UNSILOED_KEY")
    if not unsiloed_key:
        raise ValueError("UNSILOED_KEY is not configured")

    response = requests.post(
        "https://api.unsiloed.ai/v1/extraction",
        headers={"Authorization": f"Bearer {unsiloed_key}"},
        json={
            "url": image_url,
            "extract": ["amount", "payer", "date", "gstin"]
        },
        timeout=15
    )
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, dict) else {}


def get_s2_config() -> Optional[Dict[str, str]]:
    auth_token = os.getenv("S2_AUTH_TOKEN")
    basin = os.getenv("S2_BASIN")
    if not auth_token or not basin:
        return None

    return {
        "auth_token": auth_token,
        "basin": basin,
        "base_url": f"https://{basin}.b.aws.s2.dev/v1",
    }


def init_s2_stream() -> None:
    config = get_s2_config()
    if not config:
        logger.info("S2 stream init skipped: missing S2_AUTH_TOKEN or S2_BASIN")
        return

    try:
        response = requests.put(
            f"{config['base_url']}/streams/{S2_STREAM}",
            headers={"Authorization": f"Bearer {config['auth_token']}"},
            json={},
            timeout=10,
        )
        if response.status_code in (200, 201):
            logger.info("S2 stream ready: %s", S2_STREAM)
            return

        if response.status_code in (400, 409) and "already exists" in response.text.lower():
            return

        response.raise_for_status()
    except Exception as exc:
        logger.warning("Unable to initialize S2 stream: %s", exc)


def push_transaction_to_s2(tx: Dict[str, Any]) -> None:
    config = get_s2_config()
    if not config:
        return

    event_payload = {
        **tx,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    payload = {
        "records": [
            {
                "body": json.dumps(event_payload),
                "headers": ["Content-Type: application/json"],
            }
        ]
    }

    try:
        response = requests.post(
            f"{config['base_url']}/streams/{S2_STREAM}/records",
            headers={"Authorization": f"Bearer {config['auth_token']}"},
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.warning("S2 append failed: %s", exc)


def verify_razorpay_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def normalize_amount(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None

    cleaned = re.sub(r"[^\d.,]", "", value).replace(",", "")
    if not cleaned:
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_transaction_text(raw_message: str) -> Dict[str, Optional[str]]:
    message = raw_message or ""

    amount_match = re.search(r"(?i)(?:₹|rs\.?|inr)?\s*([0-9]+(?:\.[0-9]{1,2})?)", message)
    payer_match = re.search(r"(?i)(?:payer|from)\s*[:\-]?\s*([^,\n]+)", message)
    date_match = re.search(r"\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b", message)
    gstin_match = re.search(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z0-9]\b", message)

    payer = payer_match.group(1).strip() if payer_match else None
    if payer:
        payer = re.split(r"(?i)\b(?:on|date|gstin|amount|rs\.?|inr)\b", payer)[0]
        payer = re.sub(r"\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b.*$", "", payer).strip(" .,:-_")
        if not payer:
            payer = None

    return {
        "amount": amount_match.group(1) if amount_match else None,
        "payer": payer,
        "date": date_match.group(1) if date_match else None,
        "gstin": gstin_match.group(0) if gstin_match else None,
    }


async def log_transaction(
    sender: str,
    amount: Optional[float],
    payer: Optional[str],
    date: Optional[str],
    gstin: Optional[str],
    raw_message: str,
    source: str,
    raw_invoice: Optional[dict] = None,
) -> Dict[str, Any]:
    transaction = {
        "id": str(uuid.uuid4()),
        "sender": sender,
        "amount": amount,
        "payer": payer,
        "date": date,
        "gstin": gstin,
        "source": source,
        "raw_message": raw_message,
        "raw_invoice": raw_invoice,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await db.transactions.insert_one(transaction.copy())
    return transaction


def calculate_gst(amount: Optional[float]) -> Dict[str, Optional[float]]:
    gst_rate = 0.18
    if amount is None:
        return {
            "taxable_amount": None,
            "gst_rate": gst_rate,
            "gst_amount": None,
            "total_amount": None,
        }

    gst_amount = round(amount * gst_rate, 2)
    total_amount = round(amount + gst_amount, 2)
    return {
        "taxable_amount": round(amount, 2),
        "gst_rate": gst_rate,
        "gst_amount": gst_amount,
        "total_amount": total_amount,
    }


@api_router.post("/webhook/whatsapp")
@app.post("/webhook/whatsapp")
async def webhook_whatsapp(
    Body: str = Form(default=""),
    NumMedia: int = Form(default=0),
    MediaUrl0: Optional[str] = Form(default=None),
    MediaContentType0: str = Form(default=""),
    From: str = Form(default=""),
):
    amount: Optional[float] = None
    payer: Optional[str] = None
    date: Optional[str] = None
    gstin: Optional[str] = None
    invoice: Dict[str, Any] = {}
    source = "message_text"

    if NumMedia > 0 and MediaUrl0 and MediaContentType0.startswith("image/"):
        try:
            invoice = parse_invoice_image(MediaUrl0)
            amount = normalize_amount(invoice.get("amount"))
            payer = invoice.get("payer")
            date = invoice.get("date")
            gstin = invoice.get("gstin")
            if amount is not None:
                source = "invoice_image"
        except Exception as exc:
            logger.warning("Unsiloed extraction failed, using text fallback: %s", exc)

    if amount is None:
        parsed_text = parse_transaction_text(Body)
        amount = normalize_amount(parsed_text.get("amount"))
        payer = payer or parsed_text.get("payer")
        date = date or parsed_text.get("date")
        gstin = gstin or parsed_text.get("gstin")

    transaction = await log_transaction(
        sender=From,
        amount=amount,
        payer=payer,
        date=date,
        gstin=gstin,
        raw_message=Body,
        source=source,
        raw_invoice=invoice or None,
    )
    gst = calculate_gst(amount)
    push_transaction_to_s2(
        {
            "payer": payer or "Unknown",
            "amount": amount or 0.0,
            "gst": gst.get("gst_amount") or 0.0,
            "net": gst.get("total_amount") if gst.get("total_amount") is not None else (amount or 0.0),
            "source": source,
            "transaction_id": transaction["id"],
        }
    )

    return {
        "status": "processed",
        "source": source,
        "transaction": transaction,
        "gst": gst,
    }


@api_router.post("/webhook/razorpay")
@app.post("/webhook/razorpay")
async def webhook_razorpay(request: Request):
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Razorpay webhook secret not configured")

    signature = request.headers.get("X-Razorpay-Signature", "")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing Razorpay signature")

    raw_body = await request.body()
    if not verify_razorpay_signature(raw_body, signature, webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid Razorpay signature")

    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    event_name = payload.get("event", "unknown")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})

    amount_paise = payment_entity.get("amount")
    amount: Optional[float] = None
    if isinstance(amount_paise, (int, float)):
        amount = round(float(amount_paise) / 100, 2)

    payer = (
        payment_entity.get("email")
        or payment_entity.get("contact")
        or payload.get("account_id")
        or "Razorpay Payer"
    )

    created_at = payment_entity.get("created_at")
    date: Optional[str] = None
    if isinstance(created_at, (int, float)):
        date = datetime.fromtimestamp(created_at, timezone.utc).isoformat()

    transaction = await log_transaction(
        sender="razorpay",
        amount=amount,
        payer=payer,
        date=date,
        gstin=None,
        raw_message=json.dumps(payload),
        source=f"razorpay:{event_name}",
        raw_invoice=None,
    )
    gst = calculate_gst(amount)
    push_transaction_to_s2(
        {
            "payer": payer,
            "amount": amount or 0.0,
            "gst": gst.get("gst_amount") or 0.0,
            "net": gst.get("total_amount") if gst.get("total_amount") is not None else (amount or 0.0),
            "source": "razorpay",
            "transaction_id": transaction["id"],
            "event": event_name,
        }
    )

    return {
        "status": "processed",
        "event": event_name,
        "transaction": transaction,
        "gst": gst,
    }


@api_router.get("/transactions/recent")
async def get_recent_transactions(limit: int = 50):
    safe_limit = max(1, min(limit, 200))
    transactions = await db.transactions.find({}, {"_id": 0}).sort("timestamp", -1).limit(safe_limit).to_list(safe_limit)
    return {"transactions": transactions}


@app.on_event("startup")
async def startup_s2_stream():
    init_s2_stream()


# Include the router in the main app
app.include_router(api_router)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()