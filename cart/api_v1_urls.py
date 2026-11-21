from django.urls import path
from . import api_v1_views

app_name = "cart_api_v1"
urlpatterns = [
    path("", api_v1_views.detail, name="detail"),
    path("items/", api_v1_views.add_item, name="add-item"),
    path("items/<int:item_id>/", api_v1_views.item_detail, name="item-detail"),
    path("clear/", api_v1_views.clear, name="clear"),
]
