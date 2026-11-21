from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import CustomerProfile

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value.strip()).exists():
            raise serializers.ValidationError("That username is already in use.")
        return value.strip()

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        from django.contrib.auth.password_validation import validate_password
        validate_password(attrs["password"])
        return attrs


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(label="Username or email")
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")
        read_only_fields = ("id", "username")


class ProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name", required=True)
    last_name = serializers.CharField(source="user.last_name", required=True)
    email = serializers.EmailField(source="user.email", required=True)

    class Meta:
        model = CustomerProfile
        fields = ("first_name", "last_name", "email", "phone", "address", "city", "region", "country")

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.user_id).exists():
            raise serializers.ValidationError("That email address is already in use.")
        return value.lower()

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        user = instance.user
        for field in ("first_name", "last_name", "email"):
            if field in user_data:
                setattr(user, field, user_data[field])
        user.save(update_fields=["first_name", "last_name", "email"])
        return super().update(instance, validated_data)
