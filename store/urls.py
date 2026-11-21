from django.urls import path
from . import views

app_name = "store"
urlpatterns = [
    path("", views.welcome, name="welcome"),
    path("home/", views.home, name="home"),
    path("shop/", views.catalogue, name="catalogue"),
    path("shop/<slug:slug>/", views.product_detail, name="product-detail"),
]

