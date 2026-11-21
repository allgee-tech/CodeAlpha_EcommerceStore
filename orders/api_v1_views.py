from uuid import uuid4

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .api_serializers import CheckoutSerializer, OrderSerializer
from .models import Order
from .services import OrderProcessingError, cancel_order, place_order
from .forms import CheckoutForm
from drf_spectacular.utils import extend_schema, extend_schema_view


@extend_schema(request=CheckoutSerializer, responses=OrderSerializer, operation_id="v1_order_checkout")
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@extend_schema(request=CheckoutSerializer, responses=OrderSerializer, operation_id="v1_order_checkout")
def checkout(request):
    serializer = CheckoutSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = dict(serializer.validated_data)
    data.setdefault("checkout_token", uuid4())
    form = CheckoutForm(data, user=request.user)
    if not form.is_valid():
        return Response({"errors": form.errors}, status=status.HTTP_400_BAD_REQUEST)
    try:
        order, created = place_order(request.user, form.cleaned_data)
    except OrderProcessingError as error:
        return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
    response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return Response(OrderSerializer(order).data, status=response_status)


@extend_schema(responses=OrderSerializer(many=True), operation_id="v1_order_list")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@extend_schema(responses=OrderSerializer(many=True), operation_id="v1_order_list")
def order_list(request):
    orders = request.user.orders.prefetch_related("items").all()
    return Response({"count": orders.count(), "results": OrderSerializer(orders, many=True).data})


@extend_schema(responses=OrderSerializer, operation_id="v1_order_detail")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@extend_schema(responses=OrderSerializer, operation_id="v1_order_detail")
def order_detail(request, reference):
    order = request.user.orders.prefetch_related("items").filter(reference=reference).first()
    if not order:
        return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(OrderSerializer(order).data)


@extend_schema_view(post=extend_schema(request=None, responses=OrderSerializer, operation_id="v1_order_cancel"))
class CancelOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, reference):
        order = request.user.orders.filter(reference=reference).first()
        if not order:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            order = cancel_order(order.pk, request.user)
        except OrderProcessingError as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
        return Response(OrderSerializer(order).data)
