from django.contrib import admin
from django.utils.html import format_html

from .models import Holding, Stock, Trade


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = (
        "symbol",
        "name",
        "exchange",
        "yfinance_ticker",
        "last_price",
        "last_price_updated_at",
        "is_active",
    )
    list_filter = ("exchange", "is_active")
    search_fields = ("symbol", "name", "yfinance_ticker")
    ordering = ("symbol",)
    readonly_fields = ("last_price", "last_price_updated_at", "created_at", "updated_at")


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = (
        "trade_date",
        "user",
        "stock",
        "colored_trade_type",
        "quantity",
        "price",
        "total_value_display",
        "quantity_after_trade",
        "average_price_after_trade",
        "realized_pnl_display",
    )
    list_filter = ("trade_type", "stock", "trade_date")
    search_fields = ("user__email", "stock__symbol", "notes")
    date_hierarchy = "trade_date"
    ordering = ("-trade_date", "-created_at")
    autocomplete_fields = ("stock",)
    readonly_fields = (
        "average_price_after_trade",
        "quantity_after_trade",
        "realized_pnl",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (None, {"fields": ("user", "stock", "trade_type", "quantity", "price", "trade_date", "notes")}),
        (
            "Snapshot (auto-calculated, read-only)",
            {"fields": ("quantity_after_trade", "average_price_after_trade", "realized_pnl")},
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Type")
    def colored_trade_type(self, obj):
        color = "#16a34a" if obj.trade_type == "BUY" else "#dc2626"
        return format_html('<strong style="color: {}">{}</strong>', color, obj.trade_type)

    @admin.display(description="Total Value")
    def total_value_display(self, obj):
        return f"₹{obj.total_value:,.2f}"

    @admin.display(description="Realized P&L")
    def realized_pnl_display(self, obj):
        if obj.trade_type != "SELL":
            return "—"
        color = "#16a34a" if obj.realized_pnl >= 0 else "#dc2626"
        return format_html('<strong style="color: {}">₹{}</strong>', color, f"{obj.realized_pnl:,.2f}")


@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):
    """Holdings are auto-managed by portfolio.signals -> recalculate_holding().
    Read-only here by design; add/edit trades in TradeAdmin instead."""

    list_display = (
        "user",
        "stock",
        "quantity",
        "average_price",
        "total_invested",
        "current_price_display",
        "current_value_display",
        "unrealized_pnl_display",
        "realized_pnl_display",
        "updated_at",
    )
    list_filter = ("stock",)
    search_fields = ("user__email", "stock__symbol")
    ordering = ("stock__symbol",)

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    @admin.display(description="Current Price")
    def current_price_display(self, obj):
        return f"₹{obj.stock.last_price:,.2f}" if obj.stock.last_price is not None else "—"

    @admin.display(description="Current Value")
    def current_value_display(self, obj):
        value = obj.current_value
        return f"₹{value:,.2f}" if value is not None else "—"

    @admin.display(description="Unrealized P&L")
    def unrealized_pnl_display(self, obj):
        pnl = obj.unrealized_pnl
        if pnl is None:
            return "—"
        color = "#16a34a" if pnl >= 0 else "#dc2626"
        pct = obj.unrealized_pnl_percent
        pct_text = f" ({pct:,.2f}%)" if pct is not None else ""
        return format_html('<strong style="color: {}">₹{}{}</strong>', color, f"{pnl:,.2f}", pct_text)

    @admin.display(description="Realized P&L")
    def realized_pnl_display(self, obj):
        color = "#16a34a" if obj.realized_pnl >= 0 else "#dc2626"
        return format_html('<strong style="color: {}">₹{}</strong>', color, f"{obj.realized_pnl:,.2f}")
