from rest_framework import serializers


def check_phone(value: str) -> str:
    """Indian mobile numbers: exactly 10 digits."""
    if value and not (value.isdigit() and len(value) == 10):
        raise serializers.ValidationError("Enter a 10-digit phone number.")
    return value
