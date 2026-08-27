from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AppViewSet,
    DashboardViewSet,
    LoginViewSet,
    LogoutViewSet,
    StockDetailViewSet,
    TradesViewSet,
)

router = DefaultRouter()

router.register(r"", AppViewSet, basename="app")
router.register(r"login", LoginViewSet, basename="fe-login")
router.register(r"logout", LogoutViewSet, basename="fe-logout")
router.register(r"dashboard", DashboardViewSet, basename="fe-dashboard")
router.register(r"trades", TradesViewSet, basename="fe-trades")
router.register(r"holdings", StockDetailViewSet, basename="fe-holdings")

urlpatterns = [
    path("", include(router.urls)),
]
