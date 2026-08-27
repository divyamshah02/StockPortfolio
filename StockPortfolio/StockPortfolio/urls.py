from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static

urlpatterns = [
    path("django-admin/", admin.site.urls),

    # FrontEnd — page renders (no "-api" suffix, returns HTML)
    path("", include("FrontEnd.urls")),

    # API apps — all return JSON
    path("user-api/", include("accounts.urls")),
    path("portfolio-api/", include("portfolio.urls")),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
