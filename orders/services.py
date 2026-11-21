from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from cart.models import Cart, CartItem
from cart.services import effective_price
from store.models import InventoryMovement, Product
from .models import Order, OrderItem


class OrderProcessingError(ValueError):
    """A safe customer-facing checkout error."""


def delivery_fee(*, country, region=None, city=None):
    """Central delivery pricing seam; zone-specific rules can be added here later."""
    return Decimal(str(settings.DELIVERY_FEE))


def _send_confirmation(order_id):
    try:
        order = Order.objects.prefetch_related("items").get(pk=order_id)
        send_mail(
            subject=f"NOVA MARKET order {order.reference}",
            message=(f"Thank you for your order {order.reference}.\n\nOrder total: GH₵{order.total}\nPayment: {order.get_payment_method_display()}\nStatus: {order.get_status_display()}"),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            fail_silently=True,
        )
    except Exception:
        # Email delivery must never undo a committed order.
        return


@transaction.atomic
def place_order(user, cleaned_data):
    token = cleaned_data["checkout_token"]
    existing = Order.objects.filter(user=user, checkout_token=token).first()
    if existing:
        return existing, False
    cart = Cart.objects.select_for_update().filter(user=user).first()
    if not cart:
        raise OrderProcessingError("Your cart is empty.")
    cart_items = list(CartItem.objects.select_for_update().filter(cart=cart).order_by("product_id"))
    if not cart_items:
        raise OrderProcessingError("Your cart is empty.")
    product_ids = [item.product_id for item in cart_items]
    locked_products = {product.pk: product for product in Product.objects.select_for_update().filter(pk__in=product_ids)}
    subtotal = Decimal("0.00")
    for item in cart_items:
        product = locked_products.get(item.product_id)
        if not product or not product.is_active:
            raise OrderProcessingError("A product in your cart is no longer available.")
        if item.quantity < 1:
            raise OrderProcessingError(f"{product.name} has an invalid quantity.")
        if product.stock_quantity < item.quantity:
            raise OrderProcessingError(f"Only {product.stock_quantity} of {product.name} are available.")
        subtotal += effective_price(product) * item.quantity
    fee = delivery_fee(country=cleaned_data["country"], region=cleaned_data["region"], city=cleaned_data["city"])
    order = Order.objects.create(
        user=user, full_name=cleaned_data["full_name"], email=cleaned_data["email"], phone=cleaned_data["phone"],
        address=cleaned_data["address"], city=cleaned_data["city"], region=cleaned_data["region"], country=cleaned_data["country"],
        subtotal=subtotal, delivery_fee=fee, total=subtotal + fee, payment_method=cleaned_data["payment_method"],
        payment_status=Order.PaymentStatus.PENDING, status=Order.Status.CONFIRMED, checkout_token=token,
    )
    for item in cart_items:
        product = locked_products[item.product_id]
        OrderItem.objects.create(order=order, product=product, product_name=product.name, unit_price=effective_price(product), quantity=item.quantity)
        product.stock_quantity -= item.quantity
        product.save(update_fields=["stock_quantity", "updated_at"])
        InventoryMovement.objects.create(product=product, quantity_change=-item.quantity, movement_type=InventoryMovement.MovementType.SALE, reason=f"Order {order.reference}", created_by=None)
    CartItem.objects.filter(cart=cart).delete()
    transaction.on_commit(lambda: _send_confirmation(order.pk))
    return order, True


@transaction.atomic
def cancel_order(order_id, actor):
    order = Order.objects.select_for_update().prefetch_related("items").get(pk=order_id)
    if order.status == Order.Status.CANCELLED:
        raise OrderProcessingError("This order has already been cancelled.")
    if order.status not in {Order.Status.PENDING, Order.Status.CONFIRMED}:
        raise OrderProcessingError("This order can no longer be cancelled.")
    product_ids = [item.product_id for item in order.items.all() if item.product_id]
    products = {product.pk: product for product in Product.objects.select_for_update().filter(pk__in=product_ids)}
    for item in order.items.all():
        product = products.get(item.product_id)
        if not product:
            continue
        product.stock_quantity += item.quantity
        product.save(update_fields=["stock_quantity", "updated_at"])
        InventoryMovement.objects.create(product=product, quantity_change=item.quantity, movement_type=InventoryMovement.MovementType.RETURN, reason=f"Cancellation {order.reference}", created_by=actor)
    order.status = Order.Status.CANCELLED
    order.cancelled_at = timezone.now()
    order.cancelled_by = actor
    order.cancellation_requested_at = timezone.now()
    order.save(update_fields=["status", "cancelled_at", "cancelled_by", "cancellation_requested_at", "updated_at"])
    return order
