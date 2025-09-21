"""Client wrapper for interacting with the eWeb API.

The client is intentionally lightweight and focuses on the endpoints needed
for inventory and sales related MCP interactions. Credentials and connection
settings are loaded from environment variables and ``.env`` files via
:mod:`python-dotenv`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import os

import httpx
from dotenv import load_dotenv


@dataclass
class EWebCredentials:
    """Holds the credentials required for the eWeb API."""

    base_url: str
    api_key: str
    account_id: Optional[str] = None
    default_supplier_id: Optional[str] = None


class EWebClient:
    """HTTP client for the eWeb API.

    Parameters
    ----------
    base_url:
        Base URL for the eWeb instance. Defaults to the value from the
        ``EWEB_BASE_URL`` environment variable.
    api_key:
        API key or token used for authenticating with the eWeb API. Defaults to
        ``EWEB_API_KEY``.
    account_id:
        Optional account identifier used by some eWeb installations. Loaded
        from ``EWEB_ACCOUNT_ID`` when not provided.
    default_supplier_id:
        Optional default supplier identifier for inventory queries. Loaded from
        ``EWEB_DEFAULT_SUPPLIER_ID`` when not provided.
    timeout:
        Request timeout in seconds. Defaults to 30 seconds.
    """

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        account_id: Optional[str] = None,
        default_supplier_id: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        load_dotenv()

        base_url = base_url or os.getenv("EWEB_BASE_URL")
        api_key = api_key or os.getenv("EWEB_API_KEY")
        account_id = account_id or os.getenv("EWEB_ACCOUNT_ID")
        default_supplier_id = default_supplier_id or os.getenv(
            "EWEB_DEFAULT_SUPPLIER_ID"
        )

        if not base_url:
            raise ValueError("EWEB_BASE_URL must be provided via environment variables")
        if not api_key:
            raise ValueError("EWEB_API_KEY must be provided via environment variables")

        self.credentials = EWebCredentials(
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            account_id=account_id,
            default_supplier_id=default_supplier_id,
        )
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------
    def _headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.credentials.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.credentials.account_id:
            headers["X-Account-ID"] = self.credentials.account_id
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.credentials.base_url}/{path.lstrip('/')}"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.request(
                method=method,
                url=url,
                headers=self._headers(),
                params={k: v for k, v in (params or {}).items() if v is not None},
                json=json,
            )
            response.raise_for_status()
            return response.json()

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------
    def get_supplier_stock(
        self,
        *,
        supplier_id: Optional[str] = None,
        brand: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """Retrieve stock details for a supplier.

        Parameters
        ----------
        supplier_id:
            Identifier for the supplier whose inventory should be returned.
            Defaults to ``EWEB_DEFAULT_SUPPLIER_ID`` if configured.
        brand:
            Optional brand filter.
        page, page_size:
            Pagination controls passed to the API.
        """

        supplier_id = supplier_id or self.credentials.default_supplier_id
        if not supplier_id:
            raise ValueError(
                "A supplier_id is required. Configure EWEB_DEFAULT_SUPPLIER_ID or pass a value."
            )

        params = {
            "supplierId": supplier_id,
            "brand": brand,
            "page": page,
            "pageSize": page_size,
        }
        return self._request("GET", "/inventory/supplier-stock", params=params)

    def get_sales_history(
        self,
        *,
        sku: Optional[str] = None,
        upc: Optional[str] = None,
        brand: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        location_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve sales history for a SKU or brand.

        Parameters
        ----------
        sku, upc:
            Identifiers for the item whose sales history should be retrieved.
        brand:
            Optional brand-level aggregation supported by some eWeb setups.
        start_date, end_date:
            ISO-8601 formatted dates bounding the sales window.
        location_id:
            Optional location or store identifier when supported.
        """

        if not any([sku, upc, brand]):
            raise ValueError("At least one of sku, upc, or brand must be provided")

        params = {
            "sku": sku,
            "upc": upc,
            "brand": brand,
            "startDate": start_date,
            "endDate": end_date,
            "locationId": location_id,
        }
        return self._request("GET", "/sales/history", params=params)


__all__ = ["EWebClient", "EWebCredentials"]
