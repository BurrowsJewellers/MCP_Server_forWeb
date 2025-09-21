"""FastAPI application exposing MCP-compatible endpoints."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .eweb_client import EWebClient

load_dotenv()

app = FastAPI(title="eWeb MCP Server", version="0.1.0")


class IntentRequest(BaseModel):
    """Schema representing an intent expressed in natural language."""

    query: str = Field(..., description="Natural language request from the user")
    supplier_id: Optional[str] = Field(
        default=None, description="Optional supplier identifier override"
    )


class IntentResponse(BaseModel):
    """Structured response returned by the MCP server."""

    intent: str
    parameters: Dict[str, Any]
    data: Dict[str, Any]


def _extract_brand(text: str) -> Optional[str]:
    candidates = re.findall(r"\b([A-Z][A-Za-z0-9&'-]+)\b", text)
    for candidate in candidates:
        if candidate.lower() in {"show", "get", "sales", "inventory", "stock"}:
            continue
        return candidate
    return None


def _extract_time_window(text: str) -> Dict[str, str]:
    now = datetime.utcnow()
    text = text.lower()
    number_words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
    }

    match = re.search(r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)[-\s]*(day|week|month|year)s?", text)
    if match:
        quantity_raw, unit = match.groups()
        quantity = int(quantity_raw) if quantity_raw.isdigit() else number_words.get(quantity_raw, 1)
    elif "last year" in text:
        quantity, unit = 1, "year"
    elif "last month" in text:
        quantity, unit = 1, "month"
    elif "last week" in text:
        quantity, unit = 1, "week"
    else:
        return {}

    if unit.startswith("day"):
        delta = timedelta(days=quantity)
    elif unit.startswith("week"):
        delta = timedelta(weeks=quantity)
    elif unit.startswith("month"):
        delta = timedelta(days=30 * quantity)
    else:
        delta = timedelta(days=365 * quantity)

    start = now - delta
    return {"start_date": start.strftime("%Y-%m-%d"), "end_date": now.strftime("%Y-%m-%d")}


@app.post("/intent", response_model=IntentResponse)
def handle_intent(payload: IntentRequest) -> IntentResponse:
    query_lower = payload.query.lower()
    client = EWebClient()

    if any(word in query_lower for word in ["inventory", "stock"]):
        supplier_id = payload.supplier_id or client.credentials.default_supplier_id
        brand = _extract_brand(payload.query)
        if not supplier_id:
            raise HTTPException(
                status_code=400,
                detail="Supplier ID is required for inventory queries. Set EWEB_DEFAULT_SUPPLIER_ID or provide one in the request.",
            )
        params = {"supplier_id": supplier_id, "brand": brand}
        data = client.get_supplier_stock(supplier_id=supplier_id, brand=brand)
        return IntentResponse(intent="supplier_stock", parameters=params, data=data)

    if "sale" in query_lower:
        params = _extract_time_window(payload.query)
        brand = _extract_brand(payload.query)
        params.update({"brand": brand})
        if not brand:
            raise HTTPException(
                status_code=400,
                detail="Unable to determine a brand or item for the sales query. Please specify a brand name.",
            )
        data = client.get_sales_history(brand=brand, **params)
        return IntentResponse(intent="sales_history", parameters=params, data=data)

    raise HTTPException(status_code=400, detail="Unable to interpret the requested intent.")


@app.get("/healthz")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}
