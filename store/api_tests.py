from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from cart.models import Cart, CartItem
from orders.models import Order
from store.models import Category, InventoryMovement, Product

User = get_user_model()


class VersionedAPIProductTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="API Home")
        self.product = Product.objects.create(category=self.category, name="API Object", sku="API-001", description="Searchable API product", price="25.00", stock_quantity=8, is_featured=True)
        self.other = Product.objects.create(category=self.category, name="Other API Object", sku="API-002", description="Other", price="50.00", stock_quantity=0)

    def test_product_list_detail_search_filters_pagination_and_categories(self):
        response = self.client.get("/api/v1/products/", {"search": "searchable", "category": self.category.slug, "availability": "in-stock", "featured": "1", "min_price": "20", "max_price": "30", "sort": "price-asc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["name"], "API Object")
        self.assertEqual(response.data["results"][0]["price"], "25.00")
        self.assertIn("is_on_sale", response.data["results"][0])
        self.assertEqual(self.client.get(f"/api/v1/products/{self.product.pk}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/categories/{self.category.pk}/").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/categories/").status_code, 200)

    def test_invalid_api_price_filter_is_bad_request(self):
        self.assertEqual(self.client.get("/api/v1/products/?min_price=invalid").status_code, 400)


class VersionedAPIAuthenticationCartAndOrderTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        category = Category.objects.create(name="API Commerce")
        self.product = Product.objects.create(category=category, name="API Cart Product", sku="API-CART-001", description="Cart", price="30.00", stock_quantity=5)
        self.user = User.objects.create_user(username="apiuser", email="api@example.com", password="StrongPass123!", first_name="API", last_name="User")

    def checkout_payload(self, token=None):
        return {"checkout_token": str(token or uuid4()), "full_name": "API User", "email": "api@example.com", "phone": "0240000000", "address": "1 API Street", "city": "Accra", "region": "Greater Accra", "country": "Ghana", "payment_method": "cash_on_delivery"}

    def test_auth_register_login_logout_me_and_profile(self):
        self.client.post("/api/v1/auth/logout/")
        response = self.client.post("/api/v1/auth/register/", {"first_name": "New", "last_name": "API", "email": "newapi@example.com", "username": "newapi", "password": "StrongPass123!", "password_confirm": "StrongPass123!"})
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.data)
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 200)
        self.assertEqual(self.client.patch("/api/v1/accounts/profile/", {"city": "Kumasi"}, format="json").status_code, 200)
        self.client.post("/api/v1/auth/logout/")
        self.assertEqual(self.client.post("/api/v1/auth/login/", {"username": "newapi@example.com", "password": "StrongPass123!"}).status_code, 200)
        self.assertEqual(self.client.post("/api/v1/auth/login/", {"username": "newapi", "password": "wrong"}).status_code, 400)

    def test_cart_api_guest_and_authenticated_operations(self):
        response = self.client.get("/api/v1/cart/")
        self.assertEqual(response.status_code, 200)
        response = self.client.post("/api/v1/cart/items/", {"product_id": self.product.pk, "quantity": 2}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["cart"]["subtotal"], "60.00")
        self.assertEqual(self.client.patch(f"/api/v1/cart/items/{self.product.pk}/", {"quantity": 1}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/v1/cart/items/{self.product.pk}/").status_code, 204)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get("/api/v1/cart/").status_code, 200)
        self.assertEqual(self.client.post("/api/v1/cart/items/", {"product_id": self.product.pk, "quantity": 2}, format="json").status_code, 201)
        item = CartItem.objects.get(cart__user=self.user, product=self.product)
        self.assertEqual(self.client.patch(f"/api/v1/cart/items/{item.pk}/", {"quantity": 1}, format="json").status_code, 200)
        self.assertEqual(self.client.delete("/api/v1/cart/clear/").status_code, 204)

    def test_order_api_checkout_idempotency_inventory_and_permissions(self):
        self.client.force_authenticate(self.user)
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        token = uuid4()
        first = self.client.post("/api/v1/orders/checkout/", self.checkout_payload(token), format="json")
        self.assertEqual(first.status_code, 201)
        second = self.client.post("/api/v1/orders/checkout/", self.checkout_payload(token), format="json")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)
        order = Order.objects.get(user=self.user)
        self.assertEqual(self.client.get("/api/v1/orders/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/orders/{order.reference}/").status_code, 200)
        self.assertEqual(InventoryMovement.objects.filter(product=self.product, movement_type="sale").count(), 1)
        other = User.objects.create_user(username="apiother", email="apiother@example.com", password="StrongPass123!")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(f"/api/v1/orders/{order.reference}/").status_code, 404)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post(f"/api/v1/orders/{order.reference}/cancel/").status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)
