from django.urls import path
from . import api_views

app_name = "store_api"
urlpatterns = [path("products/", api_views.product_list, name="product-list"), path("categories/", api_views.category_list, name="category-list")]

