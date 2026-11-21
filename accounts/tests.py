from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cart.models import Cart, CartItem
from store.models import Category, Product

User = get_user_model()


class AuthenticationAndAccountTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Test Home")
        self.product = Product.objects.create(category=self.category, name="Test Object", sku="TEST-001", description="Test", price="20.00", stock_quantity=5)
        self.user = User.objects.create_user(username="existing", email="existing@example.com", password="StrongPass123!", first_name="Existing", last_name="Customer")

    def test_successful_registration_creates_profile_and_merges_guest_cart(self):
        session = self.client.session
        session["cart"] = {str(self.product.pk): 2}
        session.save()
        response = self.client.post(reverse("accounts:register"), {"first_name": "Ada", "last_name": "Lovelace", "email": "ada@example.com", "username": "ada", "password1": "StrongPass123!", "password2": "StrongPass123!"})
        self.assertRedirects(response, reverse("store:home"))
        user = User.objects.get(username="ada")
        self.assertTrue(hasattr(user, "profile"))
        self.assertEqual(user.cart.items.get(product=self.product).quantity, 2)
        self.assertNotIn("cart", self.client.session)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        response = self.client.post(reverse("accounts:register"), {"first_name": "A", "last_name": "B", "email": "EXISTING@example.com", "username": "different", "password1": "StrongPass123!", "password2": "StrongPass123!"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email already exists.")

    def test_invalid_registration_data_is_rejected(self):
        response = self.client.post(reverse("accounts:register"), {"first_name": "", "last_name": "B", "email": "bad", "username": "bad", "password1": "123", "password2": "456"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_login_accepts_username_or_email_and_rejects_invalid_credentials(self):
        response = self.client.post(reverse("accounts:login"), {"username": "existing@example.com", "password": "StrongPass123!"})
        self.assertRedirects(response, reverse("store:home"))
        self.client.get(reverse("accounts:logout"))
        response = self.client.post(reverse("accounts:login"), {"username": "existing", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The username or password is incorrect.")

    def test_login_rejects_external_next_redirect(self):
        response = self.client.post(reverse("accounts:login"), {"username": "existing", "password": "StrongPass123!", "next": "https://evil.example/phishing"})
        self.assertRedirects(response, reverse("store:home"))

    def test_logout_requires_post_and_terminates_session(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("store:home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_update_and_password_change(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("accounts:dashboard"), {"form_name": "profile", "profile-first_name": "Updated", "profile-last_name": "Name", "profile-email": "new@example.com", "profile-phone": "555", "profile-address": "1 Main St", "profile-city": "Austin", "profile-region": "TX", "profile-country": "United States"})
        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        response = self.client.post(reverse("accounts:dashboard"), {"form_name": "password", "password-old_password": "StrongPass123!", "password-new_password1": "NewStrongPass123!", "password-new_password2": "NewStrongPass123!"})
        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPass123!"))

    def test_protected_account_and_order_pages_redirect(self):
        self.assertRedirects(self.client.get(reverse("accounts:dashboard")), f"{reverse('accounts:login')}?next={reverse('accounts:dashboard')}")
        self.assertRedirects(self.client.get(reverse("orders:list")), f"{reverse('accounts:login')}?next={reverse('orders:list')}")


class GuestCartMergeTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name="Cart Home")
        self.product = Product.objects.create(category=category, name="Merge Object", sku="MERGE-001", description="Test", price="20.00", stock_quantity=5)
        self.user = User.objects.create_user(username="cartuser", email="cart@example.com", password="StrongPass123!")

    def test_duplicate_cart_items_combine_and_are_capped_at_stock(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=4)
        session = self.client.session
        session["cart"] = {str(self.product.pk): 4}
        session.save()
        self.client.post(reverse("accounts:login"), {"username": "cartuser", "password": "StrongPass123!"})
        item = CartItem.objects.get(cart=cart, product=self.product)
        self.assertEqual(item.quantity, 5)
        self.assertNotIn("cart", self.client.session)
