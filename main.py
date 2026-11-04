"""
Paper Trading Portfolio — FastAPI backend
Track stocks & crypto on paper. Not a broker. Not financial advice.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from db import add_holding, delete_holding, init_db, list_holdings
from prices import get_price

app = FastAPI(
    title="Paper Trading Portfolio",
    description="Paper-only stock & crypto tracker. Not financial advice.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


class HoldingIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    asset_type: str = Field(pattern="^(stock|crypto)$")
    quantity: float = Field(gt=0)
    cost_basis: float | None = Field(default=None, ge=0)
    notes: str = ""


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health():
    return {"status": "ok", "mode": "paper-trading-only"}


@app.get("/api/holdings")
async def api_list_holdings():
    holdings = list_holdings()
    enriched = []
    total_value = 0.0
    total_cost = 0.0

    for h in holdings:
        quote = await get_price(h["symbol"], h["asset_type"])
        price = quote.get("price")
        qty = h["quantity"]
        value = (price * qty) if price is not None else None
        cost = h.get("cost_basis")
        cost_total = (cost * qty) if cost is not None else None
        pnl = None
        pnl_pct = None
        if value is not None and cost_total is not None:
            pnl = value - cost_total
            pnl_pct = (pnl / cost_total * 100) if cost_total else None

        if value is not None:
            total_value += value
        if cost_total is not None:
            total_cost += cost_total

        enriched.append(
            {
                **h,
                "price": price,
                "value": value,
                "change_24h": quote.get("change_24h"),
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "quote_error": quote.get("error"),
            }
        )

    total_pnl = None
    if total_cost > 0:
        total_pnl = total_value - total_cost

    return {
        "holdings": enriched,
        "summary": {
            "total_value": total_value,
            "total_cost": total_cost if total_cost > 0 else None,
            "total_pnl": total_pnl,
            "count": len(enriched),
        },
    }


@app.post("/api/holdings")
async def api_add_holding(body: HoldingIn):
    if body.asset_type not in ("stock", "crypto"):
        raise HTTPException(400, "asset_type must be stock or crypto")
    holding = add_holding(
        symbol=body.symbol,
        asset_type=body.asset_type,
        quantity=body.quantity,
        cost_basis=body.cost_basis,
        notes=body.notes,
    )
    return {"holding": holding}


@app.delete("/api/holdings/{holding_id}")
async def api_delete_holding(holding_id: int):
    ok = delete_holding(holding_id)
    if not ok:
        raise HTTPException(404, "Holding not found")
    return {"deleted": True, "id": holding_id}


@app.get("/api/quote/{asset_type}/{symbol}")
async def api_quote(asset_type: str, symbol: str):
    if asset_type not in ("stock", "crypto"):
        raise HTTPException(400, "asset_type must be stock or crypto")
    return await get_price(symbol, asset_type)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=False)
