from rest_framework import serializers

from agreements import services
from agreements.models import Agreement


class AgreementSerializer(serializers.ModelSerializer):
    wedding_title = serializers.CharField(source="wedding.title", read_only=True)
    client_name = serializers.CharField(source="wedding.client.couple_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    certificate = serializers.SerializerMethodField()

    class Meta:
        model = Agreement
        fields = ["id", "wedding", "wedding_title", "client_name", "title", "body", "status", "status_label",
                  "sent_at", "signed_at", "created_at", "certificate"]
        read_only_fields = ["id", "status", "sent_at", "signed_at", "created_at"]

    def get_certificate(self, agreement):
        return services.certificate(agreement)


class SignSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    signature = serializers.CharField()
    code = serializers.CharField(max_length=10)
    agreed = serializers.BooleanField()
