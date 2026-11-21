from django.urls import path
from . import api_v1_views

app_name = "store_api_v1"
urlpatterns = [
    path("products/", api_v1_views.product_list, name="product-list"),
    path("products/<int:pk>/", api_v1_views.product_detail, name="product-detail"),
    path("categories/", api_v1_views.category_list, name="category-list"),
    path("categories/<int:pk>/", api_v1_views.category_detail, name="category-detail"),
]
