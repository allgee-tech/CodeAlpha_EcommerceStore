from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .api_serializers import CartItemWriteSerializer, CartQuantitySerializer, CartSerializer
from .models import Cart
from .services import CartValidationError, add_product, clear_cart, database_lines, guest_lines, remove_item, snapshot_count, snapshot_total, update_product_quantity
from drf_spectacular.utils import extend_schema, extend_schema_view


def cart_payload(request):
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        lines = database_lines(cart) if cart else []
    else:
        lines = guest_lines(request.session)
    return {"item_count": snapshot_count(lines), "subtotal": str(snapshot_total(lines)), "currency": "GHS", "items": [{"id": line.item_id, "product": {"id": line.product.pk, "name": line.product.name, "slug": line.product.slug, "price": str(line.unit_price), "stock_quantity": line.product.stock_quantity, "is_active": line.product.is_active}, "quantity": line.quantity, "unit_price": str(line.unit_price), "subtotal": str(line.subtotal), "available": line.available, "unavailable_reason": line.unavailable_reason} for line in lines]}


@extend_schema(responses=CartSerializer, operation_id="v1_cart_detail")
@api_view(["GET"])
@permission_classes([AllowAny])
@extend_schema(responses=CartSerializer, operation_id="v1_cart_detail")
def detail(request):
    return Response(cart_payload(request))


@extend_schema(request=CartItemWriteSerializer, responses=CartSerializer, operation_id="v1_cart_add_item")
@api_view(["POST"])
@permission_classes([AllowAny])
@extend_schema(request=CartItemWriteSerializer, responses=CartSerializer, operation_id="v1_cart_add_item")
def add_item(request):
    serializer = CartItemWriteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        product = add_product(request.user, request.session, serializer.validated_data.get("product_id"), serializer.validated_data["quantity"])
    except CartValidationError as error:
        return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
    return Response({"detail": "Item added.", "cart": cart_payload(request)}, status=status.HTTP_201_CREATED)


@extend_schema_view(
    patch=extend_schema(request=CartQuantitySerializer, responses=CartSerializer, operation_id="v1_cart_item_update"),
    delete=extend_schema(responses=None, operation_id="v1_cart_item_remove"),
)
@api_view(["PATCH", "DELETE"])
@permission_classes([AllowAny])
def item_detail(request, item_id):
    if request.method == "PATCH":
        serializer = CartQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            update_product_quantity(request.user, request.session, item_id, serializer.validated_data["quantity"])
        except CartValidationError as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
        return Response(cart_payload(request))
    remove_item(request.user, request.session, item_id)
    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(responses=None, operation_id="v1_cart_clear")
@api_view(["DELETE"])
@permission_classes([AllowAny])
@extend_schema(responses=None, operation_id="v1_cart_clear")
def clear(request):
    clear_cart(request.user, request.session)
    return Response(status=status.HTTP_204_NO_CONTENT)
