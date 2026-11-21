from decimal import Decimal, InvalidOperation
from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .models import Category, Product

def product_payload(product):
    return {"id": product.pk, "name": product.name, "slug": product.slug, "sku": product.sku, "description": product.description, "category": product.category.name, "category_slug": product.category.slug, "price": str(product.price), "compare_at_price": str(product.compare_at_price) if product.compare_at_price else None, "stock_quantity": product.stock_quantity, "is_featured": product.is_featured, "is_on_sale": product.is_on_sale}

@extend_schema(exclude=True)
@api_view(["GET"])
@extend_schema(exclude=True)
def product_list(request):
    products = Product.objects.filter(is_active=True).select_related("category")
    query, category, availability, featured = request.query_params.get("q", "").strip(), request.query_params.get("category", "").strip(), request.query_params.get("availability", ""), request.query_params.get("featured", "")
    if query: products = products.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(sku__icontains=query))
    if category: products = products.filter(category__slug=category)
    if availability == "in-stock": products = products.filter(stock_quantity__gt=0)
    elif availability == "out-of-stock": products = products.filter(stock_quantity=0)
    if featured == "1": products = products.filter(is_featured=True)
    try:
        if request.query_params.get("min_price"): products = products.filter(price__gte=Decimal(request.query_params["min_price"]))
        if request.query_params.get("max_price"): products = products.filter(price__lte=Decimal(request.query_params["max_price"]))
    except InvalidOperation:
        return Response({"detail": "Price filters must be valid numbers."}, status=400)
    products = products.order_by({"price-low": "price", "price-high": "-price", "oldest": "created_at", "newest": "-created_at"}.get(request.query_params.get("sort", "newest"), "-created_at"))
    return Response({"count": products.count(), "results": [product_payload(product) for product in products]})

@extend_schema(exclude=True)
@api_view(["GET"])
@extend_schema(exclude=True)
def category_list(request):
    return Response({"results": [{"name": category.name, "slug": category.slug} for category in Category.objects.all()]})
