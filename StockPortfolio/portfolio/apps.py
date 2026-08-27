from django.apps import AppConfig


class PortfolioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "portfolio"
    verbose_name = "Portfolio"

    def ready(self):
        # Connects Trade post_save/post_delete signals that keep Holding
        # rows (qty, average price, realized P&L) in sync automatically.
        from . import signals  # noqa: F401
