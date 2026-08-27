"""Thin wrapper around yfinance used for two things:

1. Verifying a symbol the user types into the "add trade" form actually
   exists on NSE, and showing them the company name + current market price
   before they confirm.
2. Refreshing Stock.last_price so Holding.current_value / unrealized_pnl on
   the dashboard stay reasonably fresh (cached for STOCK_PRICE_CACHE_MINUTES).
"""

from decimal import Decimal

from django.conf import settings
from django.utils import timezone

import yfinance as yf


def to_yfinance_ticker(symbol: str) -> str:
    """RELIANCE -> RELIANCE.NS. Leaves already-suffixed tickers untouched."""
    symbol = symbol.strip().upper()
    if "." in symbol:
        return symbol
    return f"{symbol}{settings.DEFAULT_EXCHANGE_SUFFIX}"


def fetch_quote(symbol: str):
    """Looks up a symbol on NSE via yfinance.

    Returns a dict {symbol, yfinance_ticker, name, exchange, price} on
    success, or None if the symbol could not be resolved to a real,
    currently-traded instrument.
    """
    symbol = (symbol or "").strip().upper()
    if not symbol:
        return None

    ticker = to_yfinance_ticker(symbol)

    try:
        t = yf.Ticker(ticker)
        fast_info = t.fast_info
        price = fast_info.get("lastPrice") or fast_info.get("last_price")

        if price is None:
            hist = t.history(period="1d")
            if hist.empty:
                return None
            price = float(hist["Close"].iloc[-1])

        info = {}
        try:
            info = t.get_info() or {}
        except Exception:
            info = {}

        name = info.get("longName") or info.get("shortName") or symbol

        return {
            "symbol": symbol,
            "yfinance_ticker": ticker,
            "name": name,
            "exchange": "NSE",
            "price": Decimal(str(round(float(price), 2))),
        }
    except Exception as exc:  # noqa: BLE001 - yfinance raises many different types
        print(f"[market_data] failed to fetch quote for {ticker}: {exc}")
        return None


def get_or_refresh_stock(symbol: str):
    """Get-or-create a Stock row for `symbol`, refreshing its cached price if
    it is missing or stale. Returns (stock, quote_dict_or_None)."""
    from .models import Stock

    symbol = (symbol or "").strip().upper()
    stock = Stock.objects.filter(symbol=symbol).first()

    is_stale = True
    if stock and stock.last_price_updated_at:
        age_minutes = (timezone.now() - stock.last_price_updated_at).total_seconds() / 60
        is_stale = age_minutes > settings.STOCK_PRICE_CACHE_MINUTES

    quote = None
    if stock is None or is_stale:
        quote = fetch_quote(symbol)

    if quote:
        if stock is None:
            stock = Stock.objects.create(
                symbol=quote["symbol"],
                yfinance_ticker=quote["yfinance_ticker"],
                name=quote["name"],
                exchange=quote["exchange"],
                last_price=quote["price"],
                last_price_updated_at=timezone.now(),
            )
        else:
            stock.name = quote["name"] or stock.name
            stock.last_price = quote["price"]
            stock.last_price_updated_at = timezone.now()
            stock.save(update_fields=["name", "last_price", "last_price_updated_at"])

    return stock, quote
