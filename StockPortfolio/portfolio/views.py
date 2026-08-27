from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db.models import Sum

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from utils.decorators import check_authentication, handle_exceptions

from .market_data import fetch_quote, get_or_refresh_stock
from .models import Holding, Script, Stock, Trade
from .serializers import HoldingSerializer, ScriptSerializer, StockSerializer, TradeSerializer
from .services import script_performance


def _ok(data, code=status.HTTP_200_OK):
    return Response(
        {
            "success": True,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": data,
            "error": None,
        },
        status=code,
    )


def _fail(error, code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {
            "success": False,
            "user_not_logged_in": False,
            "user_unauthorized": False,
            "data": None,
            "error": error,
        },
        status=code,
    )


def _parse_decimal(value, field_name):
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid number.")
    if d <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return d


def _parse_date(value, field_name):
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"{field_name} must be in YYYY-MM-DD format.")
    raise ValueError(f"{field_name} is required.")


# ---------------------------------------------------------------------------
# Stocks — master list + the "verify stock" check-price flow
# ---------------------------------------------------------------------------

class StockViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        search = (request.query_params.get("search") or "").strip().upper()
        qs = Stock.objects.filter(is_active=True)
        if search:
            qs = qs.filter(symbol__icontains=search)
        return _ok({"stocks": StockSerializer(qs, many=True).data})

    @handle_exceptions
    @check_authentication()
    def retrieve(self, request, pk=None):
        stock = Stock.objects.filter(pk=pk).first()
        if not stock:
            return _fail("Stock not found.", status.HTTP_404_NOT_FOUND)
        return _ok({"stock": StockSerializer(stock).data})

    @handle_exceptions
    @check_authentication()
    @action(detail=False, methods=["get"], url_path="check-price")
    def check_price(self, request):
        """GET /portfolio-api/stocks/check-price/?symbol=RELIANCE

        Confirms the symbol is a real, currently-traded NSE stock and returns
        its name + live price, WITHOUT creating a Stock row yet. Used by the
        "check" button on the add-trade form before the user confirms.
        """
        symbol = (request.query_params.get("symbol") or "").strip().upper()
        if not symbol:
            return _fail("symbol is required.")

        quote = fetch_quote(symbol)
        if not quote:
            return _fail(f"Could not verify '{symbol}'. Check the NSE symbol and try again.", status.HTTP_404_NOT_FOUND)

        return _ok({
            "symbol": quote["symbol"],
            "name": quote["name"],
            "exchange": quote["exchange"],
            "current_price": quote["price"],
        })

    @handle_exceptions
    @check_authentication()
    @action(detail=False, methods=["post"], url_path="refresh-price")
    def refresh_price(self, request):
        """POST {symbol} — force-refresh the cached last_price for a stock
        already in the master table (used on the dashboard/holdings page)."""
        symbol = (request.data.get("symbol") or "").strip().upper()
        if not symbol:
            return _fail("symbol is required.")

        stock, quote = get_or_refresh_stock(symbol)
        if not stock:
            return _fail(f"Could not verify '{symbol}'.", status.HTTP_404_NOT_FOUND)

        return _ok({"stock": StockSerializer(stock).data})


# ---------------------------------------------------------------------------
# Scripts — trading strategies the user tags trades with, so performance can
# be compared strategy-by-strategy.
# ---------------------------------------------------------------------------

def _script_summary(script, perf):
    """Flattens a Script + its script_performance() result into the shape
    used by the scripts list/detail pages (avoids repeating this in every
    action below)."""
    return {
        "id": script.id,
        "name": script.name,
        "description": script.description,
        "created_at": script.created_at,
        "trade_count": perf["trade_count"],
        "total_invested": float(perf["total_invested"]),
        "total_current_value": float(perf["total_current_value"]),
        "total_realized_pnl": float(perf["total_realized_pnl"]),
        "total_unrealized_pnl": float(perf["total_unrealized_pnl"]),
        "total_pnl": float(perf["total_realized_pnl"] + perf["total_unrealized_pnl"]),
        "has_missing_price": perf["has_missing_price"],
        "stocks_traded": len(perf["stock_breakdown"]),
    }


class ScriptViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        """GET /portfolio-api/scripts/ — every script for this user, each with
        a performance summary (trade count, invested, realized/unrealized P&L)
        so the Scripts page can render its list + comparison in one call."""
        scripts = Script.objects.filter(user=request.user).order_by("name")
        summaries = [_script_summary(s, script_performance(request.user, s)) for s in scripts]
        return _ok({"scripts": summaries})

    @handle_exceptions
    @check_authentication()
    def retrieve(self, request, pk=None):
        """GET /portfolio-api/scripts/<id>/ — full detail for the "show more"
        view: the performance summary, a per-stock breakdown, and every trade
        tagged with this script."""
        script = Script.objects.filter(pk=pk, user=request.user).first()
        if not script:
            return _fail("Script not found.", status.HTTP_404_NOT_FOUND)

        perf = script_performance(request.user, script)
        breakdown = []
        for row in perf["stock_breakdown"]:
            breakdown.append({
                **{k: v for k, v in row.items() if k not in ("average_price", "total_invested", "current_price", "current_value", "unrealized_pnl", "realized_pnl")},
                "average_price": float(row["average_price"]),
                "total_invested": float(row["total_invested"]),
                "current_price": float(row["current_price"]) if row["current_price"] is not None else None,
                "current_value": float(row["current_value"]) if row["current_value"] is not None else None,
                "unrealized_pnl": float(row["unrealized_pnl"]) if row["unrealized_pnl"] is not None else None,
                "realized_pnl": float(row["realized_pnl"]),
            })

        return _ok({
            "script": _script_summary(script, perf),
            "stock_breakdown": breakdown,
            "trades": TradeSerializer(perf["trades"], many=True).data,
        })

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        """POST {name, description?} — also used by the "add new script"
        shortcut on the trade form."""
        name = (request.data.get("name") or "").strip()
        if not name:
            return _fail("name is required.")

        if Script.objects.filter(user=request.user, name__iexact=name).exists():
            return _fail(f"You already have a script named '{name}'.")

        script = Script.objects.create(
            user=request.user,
            name=name,
            description=(request.data.get("description") or "").strip(),
        )
        return _ok({"script": ScriptSerializer(script).data}, status.HTTP_201_CREATED)

    @handle_exceptions
    @check_authentication()
    def update(self, request, pk=None):
        script = Script.objects.filter(pk=pk, user=request.user).first()
        if not script:
            return _fail("Script not found.", status.HTTP_404_NOT_FOUND)

        name = (request.data.get("name") or script.name).strip()
        if not name:
            return _fail("name is required.")
        if Script.objects.filter(user=request.user, name__iexact=name).exclude(pk=script.pk).exists():
            return _fail(f"You already have a script named '{name}'.")

        script.name = name
        script.description = request.data.get("description", script.description)
        script.save()
        return _ok({"script": ScriptSerializer(script).data})

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        script = Script.objects.filter(pk=pk, user=request.user).first()
        if not script:
            return _fail("Script not found.", status.HTTP_404_NOT_FOUND)
        script.delete()  # trades keep their history; Trade.script is SET_NULL
        return _ok({"deleted": True})


# ---------------------------------------------------------------------------
# Trades — full history, add / edit / delete a buy or sell
# ---------------------------------------------------------------------------

class TradeViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        qs = Trade.objects.filter(user=request.user).select_related("stock")

        symbol = (request.query_params.get("symbol") or "").strip().upper()
        if symbol:
            qs = qs.filter(stock__symbol=symbol)

        trade_type = (request.query_params.get("trade_type") or "").strip().upper()
        if trade_type in ("BUY", "SELL"):
            qs = qs.filter(trade_type=trade_type)

        return _ok({"trades": TradeSerializer(qs, many=True).data})

    @handle_exceptions
    @check_authentication()
    def retrieve(self, request, pk=None):
        trade = Trade.objects.filter(pk=pk, user=request.user).select_related("stock").first()
        if not trade:
            return _fail("Trade not found.", status.HTTP_404_NOT_FOUND)
        return _ok({"trade": TradeSerializer(trade).data})

    @handle_exceptions
    @check_authentication()
    def create(self, request):
        """POST /portfolio-api/trades/
        { symbol, trade_type, quantity, price, trade_date, notes? }

        `symbol` must already be a verified Stock (via check-price) — we
        get_or_create it here using the cached/live quote so the trade
        always links to a real instrument with a name + current price.
        """
        symbol = (request.data.get("symbol") or "").strip().upper()
        trade_type = (request.data.get("trade_type") or "").strip().upper()

        if not symbol:
            return _fail("symbol is required.")
        if trade_type not in ("BUY", "SELL"):
            return _fail("trade_type must be BUY or SELL.")

        try:
            quantity = int(request.data.get("quantity"))
            if quantity <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return _fail("quantity must be a whole number greater than zero.")

        try:
            price = _parse_decimal(request.data.get("price"), "price")
            trade_date = _parse_date(request.data.get("trade_date"), "trade_date")
        except ValueError as exc:
            return _fail(str(exc))

        stock, quote = get_or_refresh_stock(symbol)
        if not stock:
            return _fail(f"Could not verify '{symbol}'. Use the check button first.", status.HTTP_404_NOT_FOUND)

        script = None
        script_id = request.data.get("script")
        if script_id:
            script = Script.objects.filter(pk=script_id, user=request.user).first()
            if not script:
                return _fail("Selected script was not found.")

        if trade_type == "SELL":
            holding = Holding.objects.filter(user=request.user, stock=stock).first()
            available = holding.quantity if holding else 0
            if quantity > available:
                return _fail(
                    f"Cannot sell {quantity} shares of {stock.symbol} — you only hold {available}."
                )

        trade = Trade.objects.create(
            user=request.user,
            stock=stock,
            script=script,
            trade_type=trade_type,
            quantity=quantity,
            price=price,
            trade_date=trade_date,
            notes=(request.data.get("notes") or "").strip(),
        )
        trade.refresh_from_db()

        holding = Holding.objects.filter(user=request.user, stock=stock).first()

        return _ok({
            "trade": TradeSerializer(trade).data,
            "holding": HoldingSerializer(holding).data if holding else None,
        }, status.HTTP_201_CREATED)

    @handle_exceptions
    @check_authentication()
    def update(self, request, pk=None):
        trade = Trade.objects.filter(pk=pk, user=request.user).first()
        if not trade:
            return _fail("Trade not found.", status.HTTP_404_NOT_FOUND)

        trade_type = (request.data.get("trade_type") or trade.trade_type).strip().upper()
        if trade_type not in ("BUY", "SELL"):
            return _fail("trade_type must be BUY or SELL.")

        try:
            quantity = int(request.data.get("quantity", trade.quantity))
            if quantity <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return _fail("quantity must be a whole number greater than zero.")

        try:
            price = _parse_decimal(request.data.get("price", trade.price), "price")
            trade_date_raw = request.data.get("trade_date")
            trade_date = _parse_date(trade_date_raw, "trade_date") if trade_date_raw else trade.trade_date
        except ValueError as exc:
            return _fail(str(exc))

        if "script" in request.data:
            script_id = request.data.get("script")
            if script_id:
                script = Script.objects.filter(pk=script_id, user=request.user).first()
                if not script:
                    return _fail("Selected script was not found.")
                trade.script = script
            else:
                trade.script = None

        trade.trade_type = trade_type
        trade.quantity = quantity
        trade.price = price
        trade.trade_date = trade_date
        trade.notes = request.data.get("notes", trade.notes)
        trade.save()
        trade.refresh_from_db()

        holding = Holding.objects.filter(user=request.user, stock=trade.stock).first()

        return _ok({
            "trade": TradeSerializer(trade).data,
            "holding": HoldingSerializer(holding).data if holding else None,
        })

    @handle_exceptions
    @check_authentication()
    def destroy(self, request, pk=None):
        trade = Trade.objects.filter(pk=pk, user=request.user).first()
        if not trade:
            return _fail("Trade not found.", status.HTTP_404_NOT_FOUND)
        trade.delete()
        return _ok({"deleted": True})


# ---------------------------------------------------------------------------
# Holdings — current aggregated positions
# ---------------------------------------------------------------------------

class HoldingViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        qs = Holding.objects.filter(user=request.user).select_related("stock").order_by("stock__symbol")
        show_closed = request.query_params.get("show_closed") == "1"
        if not show_closed:
            qs = qs.filter(quantity__gt=0)
        return _ok({"holdings": HoldingSerializer(qs, many=True).data})

    @handle_exceptions
    @check_authentication()
    def retrieve(self, request, pk=None):
        """pk is the stock symbol, e.g. /portfolio-api/holdings/RELIANCE/"""
        symbol = (pk or "").strip().upper()
        stock = Stock.objects.filter(symbol=symbol).first()
        if not stock:
            return _fail("Stock not found.", status.HTTP_404_NOT_FOUND)

        holding = Holding.objects.filter(user=request.user, stock=stock).first()
        trades = Trade.objects.filter(user=request.user, stock=stock).select_related("stock")

        return _ok({
            "stock": StockSerializer(stock).data,
            "holding": HoldingSerializer(holding).data if holding else None,
            "trades": TradeSerializer(trades, many=True).data,
        })


# ---------------------------------------------------------------------------
# Dashboard — portfolio-wide summary + chart data
# ---------------------------------------------------------------------------

class DashboardViewSet(viewsets.ViewSet):

    @handle_exceptions
    @check_authentication()
    def list(self, request):
        holdings = list(
            Holding.objects.filter(user=request.user, quantity__gt=0).select_related("stock")
        )
        all_holdings = list(Holding.objects.filter(user=request.user).select_related("stock"))

        total_invested = sum((h.total_invested for h in holdings), Decimal("0"))
        total_current_value = Decimal("0")
        total_unrealized_pnl = Decimal("0")
        missing_price_for = []

        allocation = []
        gainers_losers = []

        for h in holdings:
            cv = h.current_value
            upnl = h.unrealized_pnl
            if cv is None:
                missing_price_for.append(h.stock.symbol)
            else:
                total_current_value += cv
                total_unrealized_pnl += upnl or Decimal("0")

            allocation.append({
                "symbol": h.stock.symbol,
                "value": float(cv) if cv is not None else float(h.total_invested),
            })

            gainers_losers.append({
                "symbol": h.stock.symbol,
                "quantity": h.quantity,
                "average_price": float(h.average_price),
                "current_price": float(h.current_price) if h.current_price is not None else None,
                "unrealized_pnl": float(upnl) if upnl is not None else None,
                "unrealized_pnl_percent": float(h.unrealized_pnl_percent) if h.unrealized_pnl_percent is not None else None,
            })

        total_realized_pnl = (
            Trade.objects.filter(user=request.user).aggregate(total=Sum("realized_pnl"))["total"]
            or Decimal("0")
        )

        gainers_losers.sort(key=lambda x: (x["unrealized_pnl"] if x["unrealized_pnl"] is not None else 0), reverse=True)

        recent_trades = Trade.objects.filter(user=request.user).select_related("stock")[:8]

        return _ok({
            "summary": {
                "total_invested": float(total_invested),
                "total_current_value": float(total_current_value),
                "total_unrealized_pnl": float(total_unrealized_pnl),
                "total_unrealized_pnl_percent": (
                    float((total_unrealized_pnl / total_invested) * 100) if total_invested > 0 else 0
                ),
                "total_realized_pnl": float(total_realized_pnl),
                "holdings_count": len(holdings),
                "closed_positions_count": len(all_holdings) - len(holdings),
                "missing_price_for": missing_price_for,
            },
            "allocation": allocation,
            "holdings": gainers_losers,
            "recent_trades": TradeSerializer(recent_trades, many=True).data,
        })
