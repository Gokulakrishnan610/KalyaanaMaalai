from rest_framework import serializers

from common.validators import check_phone
from vendors.models import Vendor, VendorCategory
from weddings.models import VendorRating


class VendorCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorCategory
        fields = ["id", "name"]


class VendorSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(source="category", queryset=VendorCategory.objects.all())
    category_name = serializers.CharField(source="category.name", read_only=True)
    avg_rating = serializers.SerializerMethodField()
    weddings_count = serializers.SerializerMethodField()
    phone = serializers.CharField(max_length=20)

    class Meta:
        model = Vendor
        fields = ["id", "name", "category_id", "category_name", "contact_person", "phone", "email", "city",
                  "notes", "avg_rating", "weddings_count", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_phone(self, value):
        return check_phone(value)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Enter the vendor's name.")
        return value

    def get_avg_rating(self, vendor):
        value = getattr(vendor, "avg_rating", None)
        return None if value is None else round(value, 2)

    def get_weddings_count(self, vendor):
        return getattr(vendor, "weddings_count", 0)


class RatingSerializer(serializers.ModelSerializer):
    wedding_id = serializers.IntegerField()
    wedding_title = serializers.CharField(source="wedding.title", read_only=True)
    punctuality = serializers.IntegerField(min_value=1, max_value=5)
    quality = serializers.IntegerField(min_value=1, max_value=5)
    pricing = serializers.IntegerField(min_value=1, max_value=5)

    class Meta:
        model = VendorRating
        fields = ["id", "wedding_id", "wedding_title", "punctuality", "quality", "pricing", "comment"]
        read_only_fields = ["id"]
