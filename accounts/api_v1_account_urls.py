from django.urls import path
from . import api_v1_views

app_name = "accounts_profile_api_v1"
urlpatterns = [path("profile/", api_v1_views.profile, name="profile")]
