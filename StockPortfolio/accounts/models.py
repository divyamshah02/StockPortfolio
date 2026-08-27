import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """Abstracted user model. Auth is email + password (no username field)."""

    ROLE_CHOICES = (
        ("investor", "Investor"),
        ("admin", "Admin"),
    )

    user_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="investor")

    # Base currency the portfolio is tracked in. Kept on the user so it can later
    # extend beyond INR without touching every trade/holding row.
    base_currency = models.CharField(max_length=3, default="INR")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        ordering = ["-date_joined"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email

    @property
    def is_admin(self):
        return self.role == "admin"
