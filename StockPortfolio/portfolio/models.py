from decimal import Decimal

from django.conf import settings
from django.db import models


class Stock(models.Model):
    """Master table of tradable Indian equities.

    `symbol` is the plain NSE/BSE ticker the user types (e.g. RELIANCE).
    `yfinance_ticker` is the suffixed ticker yfinance expects (e.g. RELIANCE.NS),
    used by the "verify stock" check-price call and for refreshing `last_price`.
    """

    EXCHANGE_CHOICES = (
        ("NSE", "NSE"),
        ("BSE", "BSE"),
    )

    symbol = models.CharField(max_length=20, unique=True, db_index=True)
    yfinance_ticker = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=255, blank=True)
    exchange = models.CharField(max_length=10, choices=EXCHANGE_CHOICES, default="NSE")

    # Cached last known market price, refreshed via yfinance (see services.py
    # in the market-data pass). Avoids hitting yfinance on every request.
    last_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    last_price_updated_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stocks"
        ordering = ["symbol"]
        verbose_name = "Stock"
        verbose_name_plural = "Stocks"

    def __str__(self):
        return f"{self.symbol} ({self.exchange})"


class Trade(models.Model):
    """A single buy/sell execution entered by the user.

    Every trade is stored permanently (never mutated by later trades) so the
    full trade history is always visible. `average_price_after_trade`,
    `quantity_after_trade` and `realized_pnl` are point-in-time snapshots
    recomputed by portfolio.services.recalculate_holding() whenever a trade
    for this user+stock is created, edited, or deleted - so the history stays
    accurate even if an old trade is corrected later.
    """

    TRADE_TYPE_CHOICES = (
        ("BUY", "Buy"),
        ("SELL", "Sell"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trades"
    )
    stock = models.ForeignKey(Stock, on_delete=models.PROTECT, related_name="trades")

    trade_type = models.CharField(max_length=4, choices=TRADE_TYPE_CHOICES)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)  # rate at time of trade
    trade_date = models.DateField()

    # Snapshots, filled in by recalculate_holding() - not user editable.
    average_price_after_trade = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    quantity_after_trade = models.PositiveIntegerField(null=True, blank=True)
    realized_pnl = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "trades"
        ordering = ["-trade_date", "-created_at"]
        indexes = [
            models.Index(fields=["user", "stock"]),
        ]
        verbose_name = "Trade"
        verbose_name_plural = "Trades"

    def __str__(self):
        return f"{self.user} | {self.trade_type} {self.quantity} {self.stock.symbol} @ {self.price} on {self.trade_date}"

    @property
    def total_value(self):
        return self.quantity * self.price


class Holding(models.Model):
    """Current aggregated position per user+stock. One row per (user, stock),
    kept in sync automatically from Trade history via signals -> services.recalculate_holding().
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="holdings"
    )
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="holdings")

    quantity = models.PositiveIntegerField(default=0)
    average_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    total_invested = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))

    realized_pnl = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "holdings"
        unique_together = ("user", "stock")
        ordering = ["stock__symbol"]
        verbose_name = "Holding"
        verbose_name_plural = "Holdings"

    def __str__(self):
        return f"{self.user} | {self.stock.symbol}: {self.quantity} @ avg {self.average_price}"

    @property
    def current_price(self):
        return self.stock.last_price

    @property
    def current_value(self):
        if self.stock.last_price is None:
            return None
        return self.quantity * self.stock.last_price

    @property
    def unrealized_pnl(self):
        if self.stock.last_price is None or self.quantity == 0:
            return None
        return (self.stock.last_price - self.average_price) * self.quantity

    @property
    def unrealized_pnl_percent(self):
        pnl = self.unrealized_pnl
        if pnl is None or self.total_invested == 0:
            return None
        return (pnl / self.total_invested) * Decimal("100")
