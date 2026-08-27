from rest_framework import serializers

from .models import Holding, Stock, Trade


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = (
            "id",
            "symbol",
            "yfinance_ticker",
            "name",
            "exchange",
            "last_price",
            "last_price_updated_at",
            "is_active",
        )
        read_only_fields = ("last_price", "last_price_updated_at")


class TradeSerializer(serializers.ModelSerializer):
    stock_symbol = serializers.CharField(source="stock.symbol", read_only=True)

    class Meta:
        model = Trade
        fields = (
            "id",
            "stock",
            "stock_symbol",
            "trade_type",
            "quantity",
            "price",
            "trade_date",
            "notes",
            "quantity_after_trade",
            "average_price_after_trade",
            "realized_pnl",
            "created_at",
        )
        read_only_fields = (
            "quantity_after_trade",
            "average_price_after_trade",
            "realized_pnl",
            "created_at",
        )


class HoldingSerializer(serializers.ModelSerializer):
    stock_symbol = serializers.CharField(source="stock.symbol", read_only=True)
    current_price = serializers.DecimalField(
        source="stock.last_price", max_digits=12, decimal_places=2, read_only=True
    )
    current_value = serializers.SerializerMethodField()
    unrealized_pnl = serializers.SerializerMethodField()

    class Meta:
        model = Holding
        fields = (
            "id",
            "stock",
            "stock_symbol",
            "quantity",
            "average_price",
            "total_invested",
            "current_price",
            "current_value",
            "unrealized_pnl",
            "realized_pnl",
            "updated_at",
        )

    def get_current_value(self, obj):
        return obj.current_value

    def get_unrealized_pnl(self, obj):
        return obj.unrealized_pnl
