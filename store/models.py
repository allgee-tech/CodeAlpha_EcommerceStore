from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from .validators import image_extension_validator, validate_product_image


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    sku = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    stock_quantity = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["is_active", "category"]), models.Index(fields=["name"]), models.Index(fields=["price"]), models.Index(fields=["stock_quantity"])]

        constraints = [
            models.CheckConstraint(condition=models.Q(price__gt=0), name="product_price_positive"),
            models.CheckConstraint(condition=models.Q(compare_at_price__isnull=True) | models.Q(compare_at_price__gt=models.F("price")), name="product_compare_price_above_price"),
        ]

    def clean(self):
        if self.price is not None and self.price <= 0:
            raise ValidationError({"price": "Price must be greater than zero."})
        if self.compare_at_price is not None and self.compare_at_price <= self.price:
            raise ValidationError({"compare_at_price": "Sale price must be greater than the regular price."})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def is_on_sale(self):
        return bool(self.compare_at_price and Decimal(str(self.compare_at_price)) > Decimal(str(self.price)))

    @property
    def discount_amount(self):
        return Decimal(str(self.compare_at_price)) - Decimal(str(self.price)) if self.is_on_sale else Decimal("0.00")

    @property
    def discount_percentage(self):
        if not self.is_on_sale:
            return 0
        return round((self.discount_amount / Decimal(str(self.compare_at_price))) * 100)

    def get_absolute_url(self):
        return reverse("store:product-detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/%Y/%m/", validators=[image_extension_validator, validate_product_image])
    alt_text = models.CharField(max_length=180, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-is_primary", "sort_order", "id"]

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.product}"


class InventoryMovement(models.Model):
    class MovementType(models.TextChoices):
        RESTOCK = "restock", "Restock"
        ADJUSTMENT = "adjustment", "Adjustment"
        SALE = "sale", "Sale"
        RETURN = "return", "Return"

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="inventory_movements")
    quantity_change = models.IntegerField()
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    reason = models.CharField(max_length=255)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="inventory_movements")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(condition=~models.Q(quantity_change=0), name="inventory_movement_nonzero")]
        indexes = [models.Index(fields=["product", "created_at"]), models.Index(fields=["movement_type", "created_at"])]

    def __str__(self):
        return f"{self.product} {self.quantity_change:+d} ({self.movement_type})"

