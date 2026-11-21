from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from .api_serializers import CategorySerializer, ProductSerializer
from .models import Category, Product


class CataloguePagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 50


def _filtered_products(request):
    products = Product.objects.filter(is_active=True).select_related("category").prefetch_related("images")
    query = request.query_params.get("search", request.query_params.get("q", "")).strip()
    category = request.query_params.get("category", "").strip()
    availability = request.query_params.get("availability", "")
    featured = request.query_params.get("featured", "")
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(sku__icontains=query))
    if category:
        products = products.filter(category__slug=category)
    if availability == "in-stock":
        products = products.filter(stock_quantity__gt=0)
    elif availability == "out-of-stock":
        products = products.filter(stock_quantity=0)
    elif availability == "low-stock":
        products = products.filter(stock_quantity__gt=0, stock_quantity__lte=5)
    if featured in {"1", "true", "True"}:
        products = products.filter(is_featured=True)
    try:
        if request.query_params.get("min_price"):
            products = products.filter(price__gte=Decimal(request.query_params["min_price"]))
        if request.query_params.get("max_price"):
            products = products.filter(price__lte=Decimal(request.query_params["max_price"]))
    except InvalidOperation:
        raise ValueError("Price filters must be valid numbers.")
    ordering = {"price-asc": "price", "price-low": "price", "price-desc": "-price", "price-high": "-price", "oldest": "created_at", "newest": "-created_at"}
    return products.order_by(ordering.get(request.query_params.get("sort", "newest"), "-created_at"))


@extend_schema(responses=ProductSerializer(many=True), operation_id="v1_product_list", parameters=[OpenApiParameter("search", OpenApiTypes.STR), OpenApiParameter("category", OpenApiTypes.STR), OpenApiParameter("availability", OpenApiTypes.STR), OpenApiParameter("featured", OpenApiTypes.BOOL), OpenApiParameter("min_price", OpenApiTypes.DECIMAL), OpenApiParameter("max_price", OpenApiTypes.DECIMAL), OpenApiParameter("sort", OpenApiTypes.STR)])
@api_view(["GET"])
@permission_classes([AllowAny])
@extend_schema(responses=ProductSerializer(many=True), operation_id="v1_product_list", parameters=[OpenApiParameter("search", OpenApiTypes.STR), OpenApiParameter("category", OpenApiTypes.STR), OpenApiParameter("availability", OpenApiTypes.STR), OpenApiParameter("featured", OpenApiTypes.BOOL), OpenApiParameter("min_price", OpenApiTypes.DECIMAL), OpenApiParameter("max_price", OpenApiTypes.DECIMAL), OpenApiParameter("sort", OpenApiTypes.STR)])
def product_list(request):
    try:
        products = _filtered_products(request)
    except ValueError as error:
        return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    paginator = CataloguePagination()
    page = paginator.paginate_queryset(products, request)
    return paginator.get_paginated_response(ProductSerializer(page, many=True, context={"request": request}).data)


@extend_schema(responses=ProductSerializer, operation_id="v1_product_detail")
@api_view(["GET"])
@permission_classes([AllowAny])
@extend_schema(responses=ProductSerializer, operation_id="v1_product_detail")
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related("category").prefetch_related("images"), pk=pk, is_active=True)
    return Response(ProductSerializer(product, context={"request": request}).data)


@extend_schema(responses=CategorySerializer(many=True), operation_id="v1_category_list")
@api_view(["GET"])
@permission_classes([AllowAny])
@extend_schema(responses=CategorySerializer(many=True), operation_id="v1_category_list")
def category_list(request):
    categories = Category.objects.all()
    paginator = CataloguePagination()
    page = paginator.paginate_queryset(categories, request)
    return paginator.get_paginated_response(CategorySerializer(page, many=True).data)


@extend_schema(responses=CategorySerializer, operation_id="v1_category_detail")
@api_view(["GET"])
@permission_classes([AllowAny])
@extend_schema(responses=CategorySerializer, operation_id="v1_category_detail")
def category_detail(request, pk):
    category = get_object_or_404(Category, pk=pk)
    return Response(CategorySerializer(category).data)
