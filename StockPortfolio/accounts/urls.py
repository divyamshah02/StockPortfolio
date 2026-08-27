from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AuthViewSet, SignupViewSet

router = DefaultRouter()
router.register(r"auth", AuthViewSet, basename="auth")
router.register(r"signup", SignupViewSet, basename="signup")

urlpatterns = [
    path("", include(router.urls)),
]
