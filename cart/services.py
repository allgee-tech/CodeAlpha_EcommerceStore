from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from store.models import Product
from .models import Cart, CartItem


class CartValidationError(ValueError):
    """A customer-facing cart validation error."""


@dataclass
class CartLine:
    product: Product
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    available: bool = True
    unavailable_reason: str = ""
    item_id: int = 0


def normalize_quantity(raw_quantity):
    try:
        quantity = int(raw_quantity)
    except (TypeError, ValueError):
        raise CartValidationError("Enter a valid quantity.")
    if quantity < 1:
        raise CartValidationError("Quantity must be at least 1.")
    return quantity


def effective_price(product):
    """Prices are always read from the product row, never from the browser."""
    price = Decimal(str(product.price))
    if product.compare_at_price is not None and Decimal(str(product.compare_at_price)) > price:
        return price
    return price


def line_subtotal(product, quantity):
    return effective_price(product) * normalize_quantity(quantity)


def _product_lines(product_quantities):
    product_ids = [int(product_id) for product_id in product_quantities if str(product_id).isdigit()]
    products = Product.objects.select_related("category").prefetch_related("images").filter(pk__in=product_ids)
    by_id = {product.pk: product for product in products}
    lines = []
    for raw_id, raw_quantity in product_quantities.items():
        if not str(raw_id).isdigit() or int(raw_id) not in by_id:
            continue
        product = by_id[int(raw_id)]
        try:
            quantity = normalize_quantity(raw_quantity)
        except CartValidationError:
            continue
        available = product.is_active and product.stock_quantity > 0
        reason = ""
        if not product.is_active:
            reason = "This product is no longer available."
        elif product.stock_quantity <= 0:
            reason = "This product is currently out of stock."
        elif quantity > product.stock_quantity:
            quantity = product.stock_quantity
            reason = "Quantity adjusted to the available stock."
        lines.append(CartLine(product, quantity, effective_price(product), line_subtotal(product, quantity), available, reason, product.pk))
    return lines


def guest_lines(session):
    return _product_lines(session.get("cart", {}))


def database_lines(cart):
    lines = []
    for item in cart.items.select_related("product__category").prefetch_related("product__images"):
        try:
            subtotal = line_subtotal(item.product, item.quantity)
            quantity_valid = item.quantity >= 1
        except CartValidationError:
            subtotal = Decimal("0.00")
            quantity_valid = False
        available = quantity_valid and item.product.is_active and item.product.stock_quantity > 0 and item.quantity <= item.product.stock_quantity
        reason = "" if available else ("This product is no longer available." if not item.product.is_active or item.product.stock_quantity <= 0 else "This cart quantity is invalid or exceeds current stock.")
        lines.append(CartLine(item.product, item.quantity, effective_price(item.product), subtotal, available, reason, item.pk))
    return lines


def snapshot_total(lines):
    return sum((line.subtotal for line in lines if line.available), Decimal("0.00"))


def snapshot_count(lines):
    return sum(line.quantity for line in lines if line.available)


def sanitize_session_cart(session):
    lines = guest_lines(session)
    valid = {str(line.product.pk): min(line.quantity, line.product.stock_quantity) for line in lines if line.available and line.product.stock_quantity > 0}
    if valid != session.get("cart", {}):
        if valid:
            session["cart"] = valid
        else:
            session.pop("cart", None)
        session.modified = True
    return lines


@transaction.atomic
def add_product(user, session, product_id, quantity):
    quantity = normalize_quantity(quantity)
    try:
        product = Product.objects.select_for_update().get(pk=product_id)
    except Product.DoesNotExist:
        raise CartValidationError("That product is no longer available.")
    if not product.is_active:
        raise CartValidationError("This product is no longer available.")
    if product.stock_quantity < 1:
        raise CartValidationError("This product is currently out of stock.")
    if user.is_authenticated:
        cart, _ = Cart.objects.select_for_update().get_or_create(user=user)
        item, _ = CartItem.objects.select_for_update().get_or_create(cart=cart, product=product, defaults={"quantity": 0})
        new_quantity = item.quantity + quantity
        if new_quantity > product.stock_quantity:
            raise CartValidationError(f"Only {product.stock_quantity} of {product.name} are available.")
        item.quantity = new_quantity
        item.save(update_fields=["quantity"])
    else:
        basket = dict(session.get("cart", {}))
        current = int(basket.get(str(product.pk), 0))
        if current + quantity > product.stock_quantity:
            raise CartValidationError(f"Only {product.stock_quantity} of {product.name} are available.")
        basket[str(product.pk)] = current + quantity
        session["cart"] = basket
        session.modified = True
    return product


@transaction.atomic
def update_product_quantity(user, session, item_id, quantity):
    quantity = normalize_quantity(quantity)
    if user.is_authenticated:
        try:
            item = CartItem.objects.select_for_update().select_related("product").get(pk=item_id, cart__user=user)
            product = Product.objects.select_for_update().get(pk=item.product_id)
        except (CartItem.DoesNotExist, Product.DoesNotExist):
            raise CartValidationError("That item is no longer in your bag.")
        if not product.is_active:
            raise CartValidationError("This product is no longer available.")
        if product.stock_quantity < quantity:
            raise CartValidationError(f"Only {product.stock_quantity} of {product.name} are available.")
        item.quantity = quantity
        item.save(update_fields=["quantity"])
        return product
    try:
        product = Product.objects.select_for_update().get(pk=item_id)
    except Product.DoesNotExist:
        raise CartValidationError("That item is no longer in your bag.")
    if not product.is_active or product.stock_quantity < 1:
        raise CartValidationError("This product is no longer available.")
    if quantity > product.stock_quantity:
        raise CartValidationError(f"Only {product.stock_quantity} of {product.name} are available.")
    basket = dict(session.get("cart", {}))
    if str(product.pk) not in basket:
        raise CartValidationError("That item is not in your bag.")
    basket[str(product.pk)] = quantity
    session["cart"] = basket
    session.modified = True
    return product


@transaction.atomic
def remove_item(user, session, item_id):
    if user.is_authenticated:
        CartItem.objects.select_for_update().filter(pk=item_id, cart__user=user).delete()
    else:
        basket = dict(session.get("cart", {}))
        basket.pop(str(item_id), None)
        if basket:
            session["cart"] = basket
        else:
            session.pop("cart", None)
        session.modified = True


@transaction.atomic
def clear_cart(user, session):
    if user.is_authenticated:
        CartItem.objects.select_for_update().filter(cart__user=user).delete()
    session.pop("cart", None)
    session.modified = True


def merge_session_cart(user, session):
    session_cart = dict(session.get("cart", {}))
    if not session_cart:
        return 0
    with transaction.atomic():
        cart, _ = Cart.objects.select_for_update().get_or_create(user=user)
        product_ids = [int(product_id) for product_id in session_cart if str(product_id).isdigit()]
        products = {product.pk: product for product in Product.objects.select_for_update().filter(pk__in=product_ids, is_active=True)}
        merged_count = 0
        for product_id, raw_quantity in session_cart.items():
            product = products.get(int(product_id)) if str(product_id).isdigit() else None
            if not product or product.stock_quantity <= 0:
                continue
            try:
                requested = normalize_quantity(raw_quantity)
            except CartValidationError:
                continue
            item, _ = CartItem.objects.select_for_update().get_or_create(cart=cart, product=product, defaults={"quantity": 0})
            item.quantity = min(product.stock_quantity, item.quantity + requested)
            item.save(update_fields=["quantity"])
            merged_count += item.quantity
    session.pop("cart", None)
    session.modified = True
    return merged_count
