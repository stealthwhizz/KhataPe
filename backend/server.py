from fastapi import FastAPI, APIRouter, Form
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
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
    await db.whatsapp_transactions.insert_one(transaction.copy())
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

    return {
        "status": "processed",
        "source": source,
        "transaction": transaction,
        "gst": gst,
    }


# Include the router in the main app
app.include_router(api_router)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()