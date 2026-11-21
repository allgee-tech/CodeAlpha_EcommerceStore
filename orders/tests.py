from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from cart.models import Cart, CartItem
from store.models import Category, InventoryMovement, Product
from .models import Order
from .services import OrderProcessingError, place_order

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CheckoutAndOrderTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Order Test")
        self.product = Product.objects.create(category=self.category, name="Order Object", sku="ORDER-001", description="Order test", price="80.00", compare_at_price="100.00", stock_quantity=5)
        self.other = Product.objects.create(category=self.category, name="Other Object", sku="ORDER-002", description="Other", price="10.00", stock_quantity=2)
        self.user = User.objects.create_user(username="buyer", email="buyer@example.com", password="StrongPass123!", first_name="Test", last_name="Buyer")
        self.client.force_login(self.user)
        self.cart = Cart.objects.create(user=self.user)

    def _add(self, product=None, quantity=1):
        return CartItem.objects.create(cart=self.cart, product=product or self.product, quantity=quantity)

    def _checkout_data(self, token=None, **overrides):
        data = {"checkout_token": str(token or uuid4()), "full_name": "Test Buyer", "email": "buyer@example.com", "phone": "0240000000", "address": "1 Market Street", "city": "Accra", "region": "Greater Accra", "country": "Ghana", "payment_method": Order.PaymentMethod.CASH_ON_DELIVERY}
        data.update(overrides)
        return data

    def test_unauthenticated_checkout_is_protected(self):
        self.client.logout()
        response = self.client.get(reverse("orders:checkout"))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('orders:checkout')}")

    def test_empty_cart_rejected(self):
        response = self.client.post(reverse("orders:checkout"), self._checkout_data())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your cart is empty.")
        self.assertFalse(Order.objects.exists())

    def test_successful_checkout_creates_order_deducts_stock_clears_cart_and_emails(self):
        self._add(quantity=2)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("orders:checkout"), self._checkout_data())
        order = Order.objects.get()
        self.assertRedirects(response, reverse("orders:confirmation", kwargs={"reference": order.reference}))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)
        self.assertFalse(CartItem.objects.filter(cart=self.cart).exists())
        self.assertEqual(order.subtotal, Decimal("160.00"))
        self.assertEqual(order.delivery_fee, Decimal("25.00"))
        self.assertEqual(order.total, Decimal("185.00"))
        self.assertEqual(order.payment_method, Order.PaymentMethod.CASH_ON_DELIVERY)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)
        self.assertEqual(order.status, Order.Status.CONFIRMED)
        self.assertEqual(order.items.get().product_name, "Order Object")
        self.assertEqual(order.items.get().unit_price, Decimal("80.00"))
        self.assertEqual(InventoryMovement.objects.get(product=self.product).quantity_change, -2)
        self.assertEqual(len(mail.outbox), 1)

    def test_invalid_delivery_information_is_rejected(self):
        self._add()
        response = self.client.post(reverse("orders:checkout"), self._checkout_data(address="x", phone="1"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())

    def test_insufficient_stock_rejects_without_partial_changes(self):
        self._add(quantity=6)
        response = self.client.post(reverse("orders:checkout"), self._checkout_data())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only 5")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)
        self.assertFalse(Order.objects.exists())
        self.assertTrue(CartItem.objects.filter(cart=self.cart).exists())

    def test_duplicate_submission_is_idempotent(self):
        self._add()
        token = uuid4()
        first = self.client.post(reverse("orders:checkout"), self._checkout_data(token))
        second = self.client.post(reverse("orders:checkout"), self._checkout_data(token))
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(first.url, second.url)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 4)

    def test_order_item_snapshot_survives_product_edit(self):
        self._add()
        self.client.post(reverse("orders:checkout"), self._checkout_data())
        item = Order.objects.get().items.get()
        self.product.name = "Edited Later"
        self.product.price = Decimal("95.00")
        self.product.compare_at_price = None
        self.product.save(update_fields=["name", "price", "compare_at_price"])
        item.refresh_from_db()
        self.assertEqual(item.product_name, "Order Object")
        self.assertEqual(item.unit_price, Decimal("80.00"))

    def test_order_history_and_detail_are_user_scoped(self):
        self._add()
        self.client.post(reverse("orders:checkout"), self._checkout_data())
        order = Order.objects.get()
        self.assertEqual(self.client.get(reverse("orders:list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("orders:detail", kwargs={"reference": order.reference})).status_code, 200)
        other_user = User.objects.create_user(username="other", email="other@example.com", password="StrongPass123!")
        self.client.force_login(other_user)
        self.assertEqual(self.client.get(reverse("orders:detail", kwargs={"reference": order.reference})).status_code, 404)

    def test_transaction_rolls_back_when_inventory_movement_fails(self):
        self._add()
        with patch("orders.services.InventoryMovement.objects.create", side_effect=RuntimeError("movement failure")):
            with self.assertRaises(RuntimeError):
                place_order(self.user, {**self._checkout_data(), "checkout_token": uuid4()})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)
        self.assertFalse(Order.objects.exists())
        self.assertTrue(CartItem.objects.filter(cart=self.cart).exists())

    def test_email_failure_does_not_rollback_order(self):
        self._add()
        with patch("orders.services.send_mail", side_effect=RuntimeError("mail failure")):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(reverse("orders:checkout"), self._checkout_data())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 4)

    def test_cancel_restores_stock_once_and_records_return(self):
        self._add(quantity=2)
        self.client.post(reverse("orders:checkout"), self._checkout_data())
        order = Order.objects.get()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)
        response = self.client.post(reverse("orders:cancel", kwargs={"reference": order.reference}))
        self.assertRedirects(response, reverse("orders:detail", kwargs={"reference": order.reference}))
        self.product.refresh_from_db(); order.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(InventoryMovement.objects.filter(product=self.product, movement_type=InventoryMovement.MovementType.RETURN).count(), 1)
        self.client.post(reverse("orders:cancel", kwargs={"reference": order.reference}))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)
        self.assertEqual(InventoryMovement.objects.filter(product=self.product, movement_type=InventoryMovement.MovementType.RETURN).count(), 1)

    def test_delivered_order_cannot_be_cancelled(self):
        self._add()
        self.client.post(reverse("orders:checkout"), self._checkout_data())
        order = Order.objects.get(); order.status = Order.Status.DELIVERED; order.save(update_fields=["status", "updated_at"])
        self.client.post(reverse("orders:cancel", kwargs={"reference": order.reference}))
        order.refresh_from_db(); self.product.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DELIVERED)
        self.assertEqual(self.product.stock_quantity, 4)
