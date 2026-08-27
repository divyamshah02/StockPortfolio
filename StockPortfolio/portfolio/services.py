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
