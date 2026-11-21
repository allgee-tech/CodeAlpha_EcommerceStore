from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Category, Product

User = get_user_model()


class APISecurityBoundaryTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        category = Category.objects.create(name="Security Test")
        self.product = Product.objects.create(category=category, name="Security Product", sku="SEC-001", description="Test", price="10.00", stock_quantity=2)
        self.user = User.objects.create_user(username="csrf-user", email="csrf@example.com", password="StrongPass123!")

    def test_authenticated_session_api_mutation_requires_csrf(self):
        self.assertTrue(self.client.login(username="csrf-user", password="StrongPass123!"))
        response = self.client.post("/api/v1/cart/items/", {"product_id": self.product.pk, "quantity": 1}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_order_api_is_rejected(self):
        response = self.client.get("/api/v1/orders/")
        self.assertEqual(response.status_code, 403)
