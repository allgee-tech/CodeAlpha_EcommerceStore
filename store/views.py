from decimal import Decimal, InvalidOperation
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from .models import Category, Product

IMAGE_FALLBACKS = {
    "audio": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=1000&q=85",
    "workspace": "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1000&q=85",
    "travel": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=1000&q=85",
    "home": "https://images.unsplash.com/photo-1618220179428-22790b461013?auto=format&fit=crop&w=1000&q=85",
    "wellness": "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?auto=format&fit=crop&w=1000&q=85",
}

def decorate(products):
    for product in products:
        product.display_image = product.images.first()
        product.fallback_image = IMAGE_FALLBACKS.get(product.category.slug, IMAGE_FALLBACKS["home"])
    return products

def home(request):
    featured = decorate(Product.objects.filter(is_active=True, is_featured=True).select_related("category").prefetch_related("images")[:4])
    trending = decorate(Product.objects.filter(is_active=True).select_related("category").prefetch_related("images")[:8])
    return render(request, "store/home.html", {"featured_products": featured, "trending_products": trending, "categories": Category.objects.all()})

def catalogue(request):
    products = Product.objects.filter(is_active=True).select_related("category").prefetch_related("images")
    query, category, sort = request.GET.get("q", "").strip(), request.GET.get("category", "").strip(), request.GET.get("sort", "newest")
    availability, featured = request.GET.get("availability", ""), request.GET.get("featured", "")
    min_price, max_price = request.GET.get("min_price", ""), request.GET.get("max_price", "")
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
    if featured == "1":
        products = products.filter(is_featured=True)
    try:
        if min_price: products = products.filter(price__gte=Decimal(min_price))
        if max_price: products = products.filter(price__lte=Decimal(max_price))
    except InvalidOperation:
        min_price = max_price = ""
    products = products.order_by({"price-low": "price", "price-high": "-price", "oldest": "created_at", "newest": "-created_at"}.get(sort, "-created_at"))
    page_obj = Paginator(products, 12).get_page(request.GET.get("page"))
    return render(request, "store/catalogue.html", {"page_obj": page_obj, "categories": Category.objects.all(), "filters": {"q": query, "category": category, "sort": sort, "availability": availability, "featured": featured, "min_price": min_price, "max_price": max_price}})

def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related("category").prefetch_related("images"), slug=slug, is_active=True)
    related = decorate(Product.objects.filter(is_active=True, category=product.category).exclude(pk=product.pk).select_related("category").prefetch_related("images")[:4])
    product.display_image = product.images.first()
    product.fallback_image = IMAGE_FALLBACKS.get(product.category.slug, IMAGE_FALLBACKS["home"])
    return render(request, "store/product_detail.html", {"product": product, "related_products": related})

