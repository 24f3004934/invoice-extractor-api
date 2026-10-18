
import re
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict

app = FastAPI()


class InvoiceRequest(BaseModel):
    text: str


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor: str
    amount: float
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


def extract_invoice(text: str) -> InvoiceResponse:
    if not text or not text.strip():
        raise ValueError("Empty invoice text")

    # Extract vendor
    vendor_patterns = [
        r"(?:vendor|supplier|seller|billed by|issued by|from)\s*[:\-]\s*([^\n,;]+)",
        r"\b([A-Za-z][A-Za-z0-9 &.'-]*?(?:Industries|Solutions|Technologies|Services|Systems|Enterprises|Corporation|Ltd\.?|LLC|Inc\.?))\b",
    ]

    vendor = None
    for pattern in vendor_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            vendor = match.group(1).strip()
            break

    # Extract currency
    currency_match = re.search(r"\b(USD|EUR|GBP)\b", text, re.I)

    if currency_match:
        currency = currency_match.group(1).upper()
    elif "€" in text:
        currency = "EUR"
    elif "£" in text:
        currency = "GBP"
    elif "$" in text:
        currency = "USD"
    else:
        currency = None

    # Extract amount, prioritizing total due
    amount_patterns = [
        r"(?:total\s*(?:amount\s*)?due|amount\s*due|balance\s*due|grand\s*total|total)\s*[:=\-]?\s*(?:USD|EUR|GBP|\$|€|£)?\s*([\d,]+(?:\.\d{1,2})?)",
        r"(?:USD|EUR|GBP|\$|€|£)\s*([\d,]+(?:\.\d{1,2})?)",
    ]

    amount = None
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            amount = float(match.group(1).replace(",", ""))
            break

    # Extract payment due date
    date_match = re.search(
        r"(?:due\s*date|payment\s*due|pay\s*by|due\s*on)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})",
        text,
        re.I,
    )

    if not date_match:
        date_match = re.search(r"\b(2026-\d{2}-\d{2})\b", text)

    date = date_match.group(1) if date_match else None

    if not all([vendor, amount is not None, currency, date]):
        raise ValueError("Could not extract all invoice fields")

    datetime.strptime(date, "%Y-%m-%d")

    return InvoiceResponse(
        vendor=vendor,
        amount=amount,
        currency=currency,
        date=date,
    )


@app.post("/extract", response_model=InvoiceResponse)
def extract(request: InvoiceRequest):
    try:
        return extract_invoice(request.text)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/")
def home():
    return {"status": "ok"}
