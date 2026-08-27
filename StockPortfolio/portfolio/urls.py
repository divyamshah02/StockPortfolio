from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DashboardViewSet, HoldingViewSet, StockViewSet, TradeViewSet

router = DefaultRouter()
router.register(r"stocks", StockViewSet, basename="stocks")
router.register(r"trades", TradeViewSet, basename="trades")
router.register(r"holdings", HoldingViewSet, basename="holdings")
router.register(r"dashboard", DashboardViewSet, basename="dashboard")

urlpatterns = [
    path("", include(router.urls)),
]
