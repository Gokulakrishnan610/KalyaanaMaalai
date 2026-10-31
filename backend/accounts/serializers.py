from django.contrib.auth import authenticate
from rest_framework import serializers

from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "role", "created_at"]
        read_only_fields = ["id", "created_at"]


class NewUserSerializer(UserSerializer):
    password = serializers.CharField(write_only=True, min_length=8, max_length=72)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["password"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()


class EditUserSerializer(UserSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8, max_length=72)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["password"]
        read_only_fields = UserSerializer.Meta.read_only_fields + ["email"]

    def update(self, user, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(user, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(email=data["email"].lower(), password=data["password"])
        # same message for a wrong email and a wrong password, so nobody can probe which emails exist
        if user is None or not user.is_active:
            raise serializers.ValidationError("Invalid email or password.")
        data["user"] = user
        return data
