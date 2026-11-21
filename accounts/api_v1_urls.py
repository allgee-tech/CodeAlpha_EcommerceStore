from django.urls import path
from . import api_v1_views

app_name = "accounts_api_v1"
urlpatterns = [
    path("register/", api_v1_views.register, name="register"),
    path("login/", api_v1_views.login_view, name="login"),
    path("logout/", api_v1_views.LogoutAPIView.as_view(), name="logout"),
    path("me/", api_v1_views.me, name="me"),
]
