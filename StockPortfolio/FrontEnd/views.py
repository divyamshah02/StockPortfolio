from functools import wraps

from django.contrib.auth import logout
from django.shortcuts import redirect, render

from rest_framework import viewsets

from utils.decorators import handle_exceptions


# ---------------------------------------------------------------------------
# FrontEnd-specific auth decorator — redirects to the login page instead of
# returning a JSON 401 (that's what utils.decorators.check_authentication is
# for, used by the accounts/portfolio APIs).
# ---------------------------------------------------------------------------

def fe_check_auth(required_role=None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(self, request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect("fe-login-list")

            if required_role:
                allowed = (
                    required_role
                    if isinstance(required_role, (list, tuple, set))
                    else [required_role]
                )
                if getattr(user, "role", None) not in allowed:
                    return redirect("fe-login-list")

            return view_func(self, request, *args, **kwargs)
        return _wrapped
    return decorator


# ---------------------------------------------------------------------------
# Root + auth pages
# ---------------------------------------------------------------------------

class AppViewSet(viewsets.ViewSet):

    @handle_exceptions
    def list(self, request):
        if request.user.is_authenticated:
            return redirect("fe-dashboard-list")
        return redirect("fe-login-list")


class LoginViewSet(viewsets.ViewSet):

    @handle_exceptions
    def list(self, request):
        if request.user.is_authenticated:
            return redirect("fe-dashboard-list")
        return render(request, "login.html")


class LogoutViewSet(viewsets.ViewSet):

    @handle_exceptions
    def list(self, request):
        logout(request)
        return redirect("fe-login-list")


# ---------------------------------------------------------------------------
# Portfolio pages
# ---------------------------------------------------------------------------

class DashboardViewSet(viewsets.ViewSet):

    @handle_exceptions
    @fe_check_auth()
    def list(self, request):
        return render(request, "dashboard.html", {"active_page": "dashboard"})


class TradesViewSet(viewsets.ViewSet):

    @handle_exceptions
    @fe_check_auth()
    def list(self, request):
        return render(request, "trades.html", {"active_page": "trades"})


class ScriptsViewSet(viewsets.ViewSet):

    @handle_exceptions
    @fe_check_auth()
    def list(self, request):
        return render(request, "scripts.html", {"active_page": "scripts"})


class StockDetailViewSet(viewsets.ViewSet):
    """URL: /holdings/<symbol>/ — full trade history + running average for
    a single stock."""

    @handle_exceptions
    @fe_check_auth()
    def retrieve(self, request, pk=None):
        return render(
            request,
            "stock_detail.html",
            {"active_page": "holdings", "symbol": (pk or "").strip().upper()},
        )
