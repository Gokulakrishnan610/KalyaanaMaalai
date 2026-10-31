from datetime import date

from rest_framework import serializers

from common.validators import check_phone
from portal.models import Customer

SERVICES = ["VENUE", "CATERING", "DECOR", "PHOTOGRAPHY", "MAKEUP", "MUSIC", "MEHENDI", "INVITATIONS",
            "TRANSPORT", "STAY"]
FUNCTIONS = ["ENGAGEMENT", "MEHENDI", "HALDI", "SANGEET", "WEDDING", "RECEPTION"]
CONTACTS = ["CALL", "WHATSAPP", "EMAIL"]


class SignupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(min_length=8, max_length=72, write_only=True)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Please tell us your name.")
        return value

    def validate_phone(self, value):
        return check_phone(value)

    def validate_email(self, value):
        value = value.lower()
        if Customer.objects.filter(email=value).exists():
            raise serializers.ValidationError("There is already an account with this email. Please log in.")
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class ProfileSerializer(serializers.Serializer):
    """What the couple fills in. Every field is optional so each wizard step can be saved on its own."""

    partner_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    wedding_date = serializers.DateField(required=False, allow_null=True)
    venue_city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    guest_count = serializers.IntegerField(min_value=1, max_value=5000, required=False, allow_null=True)
    budget_paise = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    functions_wanted = serializers.ListField(child=serializers.ChoiceField(choices=FUNCTIONS), required=False)
    services_needed = serializers.ListField(child=serializers.ChoiceField(choices=SERVICES), required=False)
    preferred_contact = serializers.ChoiceField(choices=CONTACTS, required=False, allow_blank=True)
    notes = serializers.CharField(max_length=2000, required=False, allow_blank=True)

    def validate_wedding_date(self, value):
        if value and value < date.today():
            raise serializers.ValidationError("The wedding date cannot be in the past.")
        return value
