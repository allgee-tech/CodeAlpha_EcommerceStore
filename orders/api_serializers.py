from rest_framework import serializers

from .models import Order, OrderItem


class CheckoutSerializer(serializers.Serializer):
    checkout_token = serializers.UUIDField(required=False)
    full_name = serializers.CharField(max_length=160, min_length=2)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=30, min_length=5)
    address = serializers.CharField(max_length=255, min_length=5)
    city = serializers.CharField(max_length=100, min_length=2)
    region = serializers.CharField(max_length=100, min_length=2)
    country = serializers.CharField(max_length=100, min_length=2)
    payment_method = serializers.ChoiceField(choices=Order.PaymentMethod.choices)


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(source="line_total", max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ("product_name", "unit_price", "quantity", "subtotal")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    payment_method_label = serializers.CharField(source="get_payment_method_display", read_only=True)
    payment_status_label = serializers.CharField(source="get_payment_status_display", read_only=True)

    class Meta:
        model = Order
        fields = ("reference", "created_at", "status", "status_label", "payment_method", "payment_method_label", "payment_status", "payment_status_label", "full_name", "email", "phone", "address", "city", "region", "country", "subtotal", "delivery_fee", "total", "items")
