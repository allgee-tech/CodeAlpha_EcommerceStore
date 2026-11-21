from django.urls import path
from . import api_v1_views

app_name = "orders_api_v1"
urlpatterns = [
    path("checkout/", api_v1_views.checkout, name="checkout"),
    path("", api_v1_views.order_list, name="list"),
    path("<str:reference>/cancel/", api_v1_views.CancelOrderAPIView.as_view(), name="cancel"),
    path("<str:reference>/", api_v1_views.order_detail, name="detail"),
]
