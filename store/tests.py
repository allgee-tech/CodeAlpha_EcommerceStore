from io import BytesIO
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from .models import Category, InventoryMovement, Product, ProductImage


class CatalogueAndInventoryTests(TestCase):
    def setUp(self):
        self.home = Category.objects.create(name="Test Home")
        self.workspace = Category.objects.create(name="Test Workspace")
        self.lamp = Product.objects.create(category=self.workspace, name="Arc Lamp", sku="CAT-001", description="A bright desk lamp", price="100.00", compare_at_price="125.00", stock_quantity=8, is_featured=True)
        self.notebook = Product.objects.create(category=self.home, name="Terra Notebook", sku="CAT-002", description="A paper notebook", price="25.00", stock_quantity=0)

    def test_product_creation_edit_and_delete(self):
        product = Product.objects.create(category=self.home, name="New Object", sku="CAT-003", description="Description", price="10.00", stock_quantity=4)
        product.name = "Edited Object"
        product.save()
        self.assertEqual(Product.objects.get(pk=product.pk).name, "Edited Object")
        product.delete()
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())

    def test_discount_calculation_and_price_validation(self):
        self.assertTrue(self.lamp.is_on_sale)
        self.assertEqual(self.lamp.discount_amount, Decimal("25.00"))
        self.assertEqual(self.lamp.discount_percentage, 20)
        invalid = Product(category=self.home, name="Invalid", sku="CAT-004", description="x", price="100.00", compare_at_price="100.00")
        with self.assertRaises(ValidationError):
            invalid.full_clean()

    def test_catalogue_search_category_price_sort_and_availability_filters(self):
        response = self.client.get(reverse("store:catalogue"), {"q": "bright", "category": self.workspace.slug, "min_price": "90", "max_price": "110", "availability": "in-stock", "featured": "1", "sort": "price-high"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Arc Lamp")
        self.assertNotContains(response, "Terra Notebook")
        response = self.client.get(reverse("store:catalogue"), {"availability": "out-of-stock"})
        self.assertContains(response, "Terra Notebook")

    def test_featured_products_are_retrieved_on_homepage(self):
        response = self.client.get(reverse("store:home"))
        self.assertContains(response, "Arc Lamp")

    def test_out_of_stock_cannot_be_added_to_cart(self):
        response = self.client.post(reverse("cart:add", args=[self.notebook.pk]))
        self.assertRedirects(response, reverse("cart:detail"))
        self.assertNotIn("cart", self.client.session)

    def test_inventory_movement_records_quantity_changes(self):
        movement = InventoryMovement.objects.create(product=self.lamp, quantity_change=5, movement_type=InventoryMovement.MovementType.RESTOCK, reason="Supplier delivery")
        self.assertEqual(self.lamp.inventory_movements.get().reason, "Supplier delivery")
        self.assertEqual(movement.quantity_change, 5)
        with self.assertRaises(IntegrityError):
            InventoryMovement.objects.create(product=self.lamp, quantity_change=0, movement_type=InventoryMovement.MovementType.ADJUSTMENT, reason="No-op")

    def test_product_image_validation_and_primary_selection(self):
        invalid = SimpleUploadedFile("malware.txt", b"not an image", content_type="text/plain")
        image = ProductImage(product=self.lamp, image=invalid)
        with self.assertRaises(ValidationError):
            image.full_clean()
        output = BytesIO()
        Image.new("RGB", (10, 10), "white").save(output, format="PNG")
        first = ProductImage.objects.create(product=self.lamp, image=SimpleUploadedFile("first.png", output.getvalue(), content_type="image/png"), is_primary=True)
        output.seek(0)
        second = ProductImage.objects.create(product=self.lamp, image=SimpleUploadedFile("second.png", output.getvalue(), content_type="image/png"), is_primary=True)
        first.refresh_from_db()
        self.assertFalse(first.is_primary)
        self.assertEqual(self.lamp.images.first().pk, second.pk)
