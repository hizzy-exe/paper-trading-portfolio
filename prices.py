"""
Price helpers — paper trading only (not financial advice, not a broker).

Crypto: CoinGecko (free, no key required for basic quotes)
Stocks: Yahoo-style quote via a simple public endpoint pattern;
        falls back gracefully if unavailable.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

# short in-memory cache so the dashboard doesn't hammer APIs
_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 60  # seconds


def _cached(key: str) -> Any | None:
    entry = _cache.get(key)
    if not entry:
        return None
    ts, data = entry
    if time.time() - ts > CACHE_TTL:
        return None
    return data


def _set_cache(key: str, data: Any) -> None:
    _cache[key] = (time.time(), data)


async def get_crypto_price(symbol: str) -> dict:
    """
    symbol examples: BTC, ETH, SOL
    CoinGecko uses ids like bitcoin, ethereum — we map common tickers.
    """
    symbol = symbol.strip().upper()
    cache_key = f"crypto:{symbol}"
    cached = _cached(cache_key)
    if cached is not None:
        return cached

    # common ticker → coingecko id
    ticker_map = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "ADA": "cardano",
        "XRP": "ripple",
        "DOGE": "dogecoin",
        "DOT": "polkadot",
        "AVAX": "avalanche-2",
        "MATIC": "matic-network",
        "LINK": "chainlink",
        "LTC": "litecoin",
        "ATOM": "cosmos",
        "UNI": "uniswap",
        "BNB": "binancecoin",
    }
    coin_id = ticker_map.get(symbol, symbol.lower())

    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": coin_id,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    if coin_id not in data:
        result = {
            "symbol": symbol,
            "asset_type": "crypto",
            "price": None,
            "change_24h": None,
            "error": f"Unknown crypto symbol or id: {symbol}",
        }
    else:
        result = {
            "symbol": symbol,
            "asset_type": "crypto",
            "price": data[coin_id].get("usd"),
            "change_24h": data[coin_id].get("usd_24h_change"),
            "error": None,
        }

    _set_cache(cache_key, result)
    return result


async def get_stock_price(symbol: str) -> dict:
    """
    Basic stock quote via Yahoo finance-style public endpoint.
    Paper use only — not for production trading decisions.
    """
    symbol = symbol.strip().upper()
    cache_key = f"stock:{symbol}"
    cached = _cached(cache_key)
    if cached is not None:
        return cached

    # Yahoo chart API (commonly used for simple quotes; can change over time)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"range": "1d", "interval": "1m"}
    headers = {"User-Agent": "Mozilla/5.0 (paper-portfolio-student-project)"}

    try:
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        result_block = (data.get("chart") or {}).get("result") or []
        if not result_block:
            raise ValueError("No quote data")

        meta = result_block[0].get("meta") or {}
        price = meta.get("regularMarketPrice") or meta.get("previousClose")
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        change_pct = None
        if price is not None and prev:
            change_pct = ((price - prev) / prev) * 100

        result = {
            "symbol": symbol,
            "asset_type": "stock",
            "price": price,
            "change_24h": change_pct,
            "error": None,
        }
    except Exception as exc:
        result = {
            "symbol": symbol,
            "asset_type": "stock",
            "price": None,
            "change_24h": None,
            "error": str(exc),
        }

    _set_cache(cache_key, result)
    return result


async def get_price(symbol: str, asset_type: str) -> dict:
    asset_type = asset_type.lower()
    if asset_type == "crypto":
        return await get_crypto_price(symbol)
    if asset_type == "stock":
        return await get_stock_price(symbol)
    return {
        "symbol": symbol,
        "asset_type": asset_type,
        "price": None,
        "change_24h": None,
        "error": "asset_type must be 'stock' or 'crypto'",
    }
