# Paper Trading Portfolio

Paper-only tracker for **stocks** and **crypto**.

Not a broker. Not financial advice. No real trades.

## Stack

- FastAPI + SQLite
- CoinGecko (crypto quotes)
- Yahoo chart endpoint (stock quotes, best-effort)
- Simple HTML/JS dashboard

## Run locally

```bash
cd paper-trading-portfolio
python -m venv .venv
# Windows:
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

Open: http://127.0.0.1:8001

## API (quick)

- `GET /api/holdings` — list + live prices + summary
- `POST /api/holdings` — add holding JSON
- `DELETE /api/holdings/{id}` — remove
- `GET /api/quote/{stock|crypto}/{SYMBOL}` — single quote

## Next (path to SaaS)

1. User accounts (auth)
2. Per-user holdings
3. Stripe free/paid plans
4. Deploy always-on host
