from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Trade
from .services import recalculate_holding


@receiver(post_save, sender=Trade)
def on_trade_saved(sender, instance, **kwargs):
    recalculate_holding(instance.user, instance.stock)


@receiver(post_delete, sender=Trade)
def on_trade_deleted(sender, instance, **kwargs):
    recalculate_holding(instance.user, instance.stock)
