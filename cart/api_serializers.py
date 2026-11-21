from rest_framework import serializers


class CartItemWriteSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1, required=True)
    quantity = serializers.IntegerField(min_value=1)


class CartQuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class CartSerializer(serializers.Serializer):
    item_count = serializers.IntegerField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    items = serializers.ListField(child=serializers.DictField())
