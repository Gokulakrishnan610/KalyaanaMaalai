from django.db.models import Sum
from django.db.models.functions import Coalesce
from rest_framework import serializers

from clients.models import Client
from clients.services import find_client
from common.validators import check_phone
from payments.models import Invoice, Payment
from weddings.models import Wedding


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ["id", "couple_name", "client_name", "spouse_name", "spouse_email", "bride_name", "groom_name",
                  "phone", "email", "city", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_phone(self, value):
        return check_phone(value)

    def validate(self, attrs):
        # one client per client name + email: say who already has it instead of failing in the database
        name = attrs.get("client_name", self.instance.client_name if self.instance else "")
        email = attrs.get("email", self.instance.email if self.instance else "")
        existing = find_client(name, email)
        if existing and (self.instance is None or existing.pk != self.instance.pk):
            raise serializers.ValidationError(
                {"email": f"{existing.client_name or existing.couple_name} is already a client with this email."})
        return attrs


class ClientWeddingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wedding
        fields = ["id", "title", "start_date", "city", "guest_count", "status"]


class ClientProfileSerializer(ClientSerializer):
    """The client page: couple details, enquiry history, weddings and what they still owe us."""

    enquiries = serializers.SerializerMethodField()
    weddings = ClientWeddingSerializer(many=True, read_only=True)
    invoiced_paise = serializers.SerializerMethodField()
    paid_paise = serializers.SerializerMethodField()
    outstanding_paise = serializers.SerializerMethodField()

    class Meta(ClientSerializer.Meta):
        fields = ClientSerializer.Meta.fields + [
            "enquiries", "weddings", "invoiced_paise", "paid_paise", "outstanding_paise",
        ]

    def get_enquiries(self, client):
        return [
            {"id": e.id, "source": e.source, "status": e.status, "created_at": e.created_at}
            for e in client.enquiries.all()
        ]

    def get_invoiced_paise(self, client):
        return Invoice.objects.filter(client=client).aggregate(t=Coalesce(Sum("amount_paise"), 0))["t"]

    def get_paid_paise(self, client):
        return Payment.objects.filter(invoice__client=client, direction=Payment.Direction.IN).aggregate(
            t=Coalesce(Sum("amount_paise"), 0))["t"]

    def get_outstanding_paise(self, client):
        return self.get_invoiced_paise(client) - self.get_paid_paise(client)
