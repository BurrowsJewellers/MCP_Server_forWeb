# MCP Server for eWeb Integrations

This project provides a minimal FastAPI-based MCP (Model Context Protocol) server
that translates natural-language retail operations requests into eWeb API
calls. It wraps the supplier stock and sales history endpoints, enabling ChatGPT
and other MCP-compatible clients to surface inventory and sales insights.

## Project Layout

```
.
├── requirements.txt      # Python dependencies
└── src/
    ├── __init__.py
    ├── eweb_client.py    # HTTP wrapper around the eWeb API
    └── mcp_server.py     # FastAPI application exposing MCP endpoints
```

## Prerequisites

* Python 3.10+
* pip (or another PEP 517 compatible installer)

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Credentials and connection details are loaded from environment variables. You
can set them directly in your shell or create a `.env` file in the project root.

Required variables:

* `EWEB_BASE_URL` – Base URL for the eWeb instance (e.g., `https://example.com/api`).
* `EWEB_API_KEY` – API key or bearer token.

Optional variables:

* `EWEB_ACCOUNT_ID` – Account header required by some deployments.
* `EWEB_DEFAULT_SUPPLIER_ID` – Default supplier identifier used for stock queries.

Example `.env` file:

```
EWEB_BASE_URL=https://example.com/api
EWEB_API_KEY=replace-me
EWEB_ACCOUNT_ID=demo-account
EWEB_DEFAULT_SUPPLIER_ID=12345
```

## Running the Server

Activate your virtual environment (if applicable) and start the FastAPI
application with Uvicorn:

```bash
uvicorn src.mcp_server:app --reload --port 8000
```

The server exposes a health endpoint at `GET /healthz` and an intent processing
endpoint at `POST /intent`.

## Example Request Flow

1. **ChatGPT (or another MCP client) request**

   Natural language prompt: “Citizen Watches six-month sales.”

2. **Server interpretation**

   The `/intent` endpoint converts the request into a sales history query. You
   can test locally with curl:

   ```bash
   curl -X POST http://localhost:8000/intent \
        -H "Content-Type: application/json" \
        -d '{"query": "Citizen Watches six-month sales"}'
   ```

3. **Sample response**

   ```json
   {
     "intent": "sales_history",
     "parameters": {
       "start_date": "2024-03-17",
       "end_date": "2024-09-13",
       "brand": "Citizen"
     },
     "data": {
       "...": "JSON payload returned from the eWeb /sales/history endpoint"
     }
   }
   ```

Swap the prompt to "Citizen inventory status" (or supply a different supplier ID
and brand) to receive stock details via the `supplier_stock` action.

## Development Notes

* The eWeb client currently supports supplier stock and sales history endpoints.
  Additional endpoints can be added following the same pattern in
  `src/eweb_client.py`.
* Authentication headers assume bearer token usage. Adjust the `_headers`
  implementation if your deployment requires another scheme.
