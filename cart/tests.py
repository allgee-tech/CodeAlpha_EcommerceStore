from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from store.models import Category, Product
from .models import Cart, CartItem

User = get_user_model()


class CartWorkflowTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name="Cart Test")
        self.product = Product.objects.create(category=category, name="Cart Object", sku="CART-001", description="Cart test product", price="12.50", compare_at_price="20.00", stock_quantity=8)
        self.second = Product.objects.create(category=category, name="Second Object", sku="CART-002", description="Second product", price="5.25", stock_quantity=3)
        self.user = User.objects.create_user(username="cart-test", email="cart-test@example.com", password="StrongPass123!")

    def test_guest_add_persists_and_calculates_decimal_totals(self):
        response = self.client.post(reverse("cart:add", args=[self.product.pk]), {"quantity": 2})
        self.assertRedirects(response, reverse("cart:detail"))
        self.assertEqual(self.client.session["cart"][str(self.product.pk)], 2)
        response = self.client.get(reverse("cart:detail"))
        self.assertContains(response, "GH₵12.50")
        self.assertContains(response, "GH₵25.00")

    def test_guest_increase_decrease_remove_and_clear(self):
        self.client.post(reverse("cart:add", args=[self.product.pk]), {"quantity": 2})
        self.client.post(reverse("cart:update", args=[self.product.pk]), {"quantity": 3})
        self.assertEqual(self.client.session["cart"][str(self.product.pk)], 3)
        self.client.post(reverse("cart:update", args=[self.product.pk]), {"quantity": 1})
        self.assertEqual(self.client.session["cart"][str(self.product.pk)], 1)
        self.client.post(reverse("cart:remove", args=[self.product.pk]))
        self.assertNotIn("cart", self.client.session)
        self.client.post(reverse("cart:add", args=[self.product.pk]))
        self.client.post(reverse("cart:add", args=[self.second.pk]))
        self.client.post(reverse("cart:clear"))
        self.assertNotIn("cart", self.client.session)

    def test_invalid_quantities_and_stock_are_rejected(self):
        response = self.client.post(reverse("cart:add", args=[self.product.pk]), {"quantity": 9})
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("cart", self.client.session)
        self.client.post(reverse("cart:add", args=[self.product.pk]), {"quantity": 2})
        response = self.client.post(reverse("cart:update", args=[self.product.pk]), {"quantity": 0})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session["cart"][str(self.product.pk)], 2)
        self.product.stock_quantity = 0
        self.product.save(update_fields=["stock_quantity"])
        response = self.client.post(reverse("cart:update", args=[self.product.pk]), {"quantity": 1})
        self.assertEqual(response.status_code, 302)

    def test_inactive_and_out_of_stock_products_are_rejected(self):
        self.product.is_active = False
        self.product.save(update_fields=["is_active"])
        response = self.client.post(reverse("cart:add", args=[self.product.pk]))
        self.assertEqual(response.status_code, 302)
        self.product.is_active = True
        self.product.stock_quantity = 0
        self.product.save(update_fields=["is_active", "stock_quantity"])
        response = self.client.post(reverse("cart:add", args=[self.product.pk]))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_cart_persists_and_uses_current_price(self):
        self.client.force_login(self.user)
        self.client.post(reverse("cart:add", args=[self.product.pk]), {"quantity": 2})
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.get(product=self.product).quantity, 2)
        self.product.price = Decimal("15.00")
        self.product.save(update_fields=["price"])
        response = self.client.get(reverse("cart:detail"))
        self.assertContains(response, "GH₵15.00")
        self.assertContains(response, "GH₵30.00")

    def test_authenticated_cart_update_remove_and_clear(self):
        self.client.force_login(self.user)
        self.client.post(reverse("cart:add", args=[self.product.pk]), {"quantity": 2})
        item = CartItem.objects.get(cart__user=self.user, product=self.product)
        self.client.post(reverse("cart:update", args=[item.pk]), {"quantity": 1})
        self.assertEqual(CartItem.objects.get(pk=item.pk).quantity, 1)
        self.client.post(reverse("cart:remove", args=[item.pk]))
        self.assertFalse(CartItem.objects.filter(pk=item.pk).exists())
        self.client.post(reverse("cart:add", args=[self.second.pk]))
        self.client.post(reverse("cart:clear"))
        self.assertFalse(CartItem.objects.filter(cart__user=self.user).exists())
