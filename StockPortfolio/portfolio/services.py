"""Business logic for keeping Holding rows and Trade snapshots in sync.

Rebuilds the full position for a given (user, stock) from the complete trade
history every time a trade is added/edited/deleted, rather than incrementally
patching numbers. This is deliberately simple and self-healing: correcting an
old trade, or deleting one, automatically fixes every average/P&L figure
downstream of it.

Weighted-average costing (the standard method for equity portfolios):
  - BUY:  new_qty = old_qty + qty
          new_invested = old_invested + (qty * price)
          new_avg = new_invested / new_qty
  - SELL: realized_pnl_for_trade = (sell_price - avg_price_before) * qty
          new_qty = old_qty - qty
          new_invested = new_avg_before * new_qty   (average price is unchanged by a sell)
"""

from decimal import ROUND_HALF_UP, Decimal


def _round2(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def recalculate_holding(user, stock):
    """Recomputes the Holding row for (user, stock) from scratch and backfills
    the snapshot fields (average_price_after_trade, quantity_after_trade,
    realized_pnl) on every Trade row for that user+stock, in chronological order."""
    from .models import Holding, Trade

    trades = Trade.objects.filter(user=user, stock=stock).order_by("trade_date", "created_at", "id")

    qty = Decimal("0")
    avg_price = Decimal("0")
    invested = Decimal("0")
    realized_pnl_total = Decimal("0")

    for trade in trades:
        trade_qty = Decimal(trade.quantity)

        if trade.trade_type == "BUY":
            invested += trade_qty * trade.price
            qty += trade_qty
            avg_price = (invested / qty) if qty > 0 else Decimal("0")
            trade_realized_pnl = Decimal("0")

        else:  # SELL
            trade_realized_pnl = (trade.price - avg_price) * trade_qty
            realized_pnl_total += trade_realized_pnl
            qty -= trade_qty
            invested = avg_price * qty  # average price unchanged on a sell
            if qty <= 0:
                qty = Decimal("0")
                invested = Decimal("0")
                avg_price = Decimal("0")

        Trade.objects.filter(pk=trade.pk).update(
            average_price_after_trade=_round2(avg_price),
            quantity_after_trade=int(qty),
            realized_pnl=_round2(trade_realized_pnl),
        )

    holding, _ = Holding.objects.get_or_create(user=user, stock=stock)
    holding.quantity = int(qty)
    holding.average_price = _round2(avg_price)
    holding.total_invested = _round2(invested)
    holding.realized_pnl = _round2(realized_pnl_total)
    holding.save(update_fields=["quantity", "average_price", "total_invested", "realized_pnl", "updated_at"])
    return holding


# ---------------------------------------------------------------------------
# Script performance — same weighted-average logic, scoped to trades tagged
# with one Script instead of the user's full holding. Used to answer "which
# of my trading scripts is actually making money".
# ---------------------------------------------------------------------------

def _compute_stats_from_trades(trades):
    """Runs the same weighted-average-costing loop as recalculate_holding()
    over an arbitrary ordered list of Trade rows (e.g. just the trades for
    one script + one stock) and returns the resulting aggregate — without
    writing anything back to the database."""
    qty = Decimal("0")
    avg_price = Decimal("0")
    invested = Decimal("0")
    realized_pnl_total = Decimal("0")

    for trade in trades:
        trade_qty = Decimal(trade.quantity)

        if trade.trade_type == "BUY":
            invested += trade_qty * trade.price
            qty += trade_qty
            avg_price = (invested / qty) if qty > 0 else Decimal("0")

        else:  # SELL
            realized_pnl_total += (trade.price - avg_price) * trade_qty
            qty -= trade_qty
            invested = avg_price * qty
            if qty <= 0:
                qty = Decimal("0")
                invested = Decimal("0")
                avg_price = Decimal("0")

    return {
        "quantity": int(qty),
        "average_price": _round2(avg_price),
        "total_invested": _round2(invested),
        "realized_pnl": _round2(realized_pnl_total),
    }


def script_performance(user, script):
    """Aggregates every trade tagged with `script` (grouped per stock, since
    a script may trade several stocks) into a performance summary: total
    invested, current value, realized + unrealized P&L, and a per-stock
    breakdown for the "show more" detail view."""
    from .models import Trade

    trades = list(
        Trade.objects.filter(user=user, script=script)
        .select_related("stock")
        .order_by("trade_date", "created_at", "id")
    )

    by_stock = {}
    for trade in trades:
        by_stock.setdefault(trade.stock_id, {"stock": trade.stock, "trades": []})["trades"].append(trade)

    total_invested = Decimal("0")
    total_current_value = Decimal("0")
    total_realized_pnl = Decimal("0")
    total_unrealized_pnl = Decimal("0")
    has_missing_price = False
    stock_breakdown = []

    for bucket in by_stock.values():
        stock = bucket["stock"]
        stats = _compute_stats_from_trades(bucket["trades"])

        current_price = stock.last_price
        current_value = None
        unrealized_pnl = None
        if stats["quantity"] > 0:
            if current_price is not None:
                current_value = _round2(stats["quantity"] * current_price)
                unrealized_pnl = _round2((current_price - stats["average_price"]) * stats["quantity"])
            else:
                has_missing_price = True

        total_invested += stats["total_invested"]
        total_realized_pnl += stats["realized_pnl"]
        total_current_value += current_value or Decimal("0")
        total_unrealized_pnl += unrealized_pnl or Decimal("0")

        stock_breakdown.append({
            "stock_id": stock.id,
            "symbol": stock.symbol,
            "name": stock.name,
            "quantity": stats["quantity"],
            "average_price": stats["average_price"],
            "total_invested": stats["total_invested"],
            "current_price": current_price,
            "current_value": current_value,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": stats["realized_pnl"],
            "trade_count": len(bucket["trades"]),
        })

    stock_breakdown.sort(key=lambda x: x["symbol"])

    return {
        "trade_count": len(trades),
        "total_invested": _round2(total_invested),
        "total_current_value": _round2(total_current_value),
        "total_realized_pnl": _round2(total_realized_pnl),
        "total_unrealized_pnl": _round2(total_unrealized_pnl),
        "has_missing_price": has_missing_price,
        "stock_breakdown": stock_breakdown,
        "trades": trades,
    }
