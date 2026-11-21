from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view

from cart.services import merge_session_cart
from .api_serializers import LoginSerializer, ProfileSerializer, RegisterSerializer, UserSerializer
from .models import CustomerProfile

User = get_user_model()


class AuthRateThrottle(AnonRateThrottle):
    scope = "auth"


@extend_schema(request=RegisterSerializer, responses=UserSerializer, operation_id="v1_auth_register")
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
@extend_schema(request=RegisterSerializer, responses=UserSerializer, operation_id="v1_auth_register")
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    with transaction.atomic():
        user = User.objects.create_user(username=data["username"], email=data["email"], password=data["password"], first_name=data["first_name"], last_name=data["last_name"])
        CustomerProfile.objects.create(user=user)
        login(request, user)
        merge_session_cart(user, request.session)
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema(request=LoginSerializer, responses=UserSerializer, operation_id="v1_auth_login")
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthRateThrottle])
@extend_schema(request=LoginSerializer, responses=UserSerializer, operation_id="v1_auth_login")
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    identifier = serializer.validated_data["username"].strip()
    user_by_email = User.objects.filter(email__iexact=identifier).first()
    username = user_by_email.username if user_by_email else identifier
    user = authenticate(request, username=username, password=serializer.validated_data["password"])
    if user is None:
        return Response({"detail": "The username or password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
    login(request, user)
    merge_session_cart(user, request.session)
    return Response(UserSerializer(user).data)


@extend_schema(responses=UserSerializer, operation_id="v1_auth_me")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@extend_schema(responses=UserSerializer, operation_id="v1_auth_me")
def me(request):
    return Response(UserSerializer(request.user).data)


@extend_schema_view(
    get=extend_schema(responses=ProfileSerializer, operation_id="v1_account_profile_get"),
    patch=extend_schema(request=ProfileSerializer, responses=ProfileSerializer, operation_id="v1_account_profile_patch"),
)
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def profile(request):
    instance, _ = CustomerProfile.objects.get_or_create(user=request.user)
    if request.method == "PATCH":
        serializer = ProfileSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    else:
        serializer = ProfileSerializer(instance)
    return Response(serializer.data)

@extend_schema_view(post=extend_schema(request=None, responses={204: None}, operation_id="v1_auth_logout"))
class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
