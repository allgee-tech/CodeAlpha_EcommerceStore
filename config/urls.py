from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.http import JsonResponse
from django.db import connection


def health(request):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unhealthy", "database": "unavailable"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls), path("", include("store.urls")),
    path("account/", include("accounts.urls")), path("cart/", include("cart.urls")),
    path("orders/", include("orders.urls")), path("api/", include("store.api_urls")),
    path("api/v1/", include("store.api_v1_urls")),
    path("api/v1/auth/", include("accounts.api_v1_urls")),
    path("api/v1/accounts/", include("accounts.api_v1_account_urls")),
    path("api/v1/cart/", include("cart.api_v1_urls")),
    path("api/v1/orders/", include("orders.api_v1_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="api-schema"), name="api-redoc"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

