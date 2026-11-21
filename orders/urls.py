from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

app_name = "orders"
urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("", views.order_list, name="list"),
    path("<str:reference>/confirmation/", views.confirmation, name="confirmation"),
    path("<str:reference>/cancel/", views.cancel, name="cancel"),
    path("<str:reference>/", views.order_detail, name="detail"),
]

