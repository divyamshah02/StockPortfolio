from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "user_id",
            "email",
            "full_name",
            "role",
            "base_currency",
            "is_active",
            "date_joined",
        )
        read_only_fields = ("user_id", "role", "is_active", "date_joined")
