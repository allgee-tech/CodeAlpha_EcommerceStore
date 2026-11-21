from django.contrib import admin
from django.utils.html import format_html
from .models import Category, InventoryMovement, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ("image_preview",)

    @admin.display(description="Preview")
    def image_preview(self, obj):
        if not obj or not obj.image:
            return "—"
        return format_html('<img src="{}" style="max-height:80px;max-width:120px;object-fit:cover" alt="{}">', obj.image.url, obj.alt_text or obj.product.name)


class InventoryMovementInline(admin.TabularInline):
    model = InventoryMovement
    extra = 0
    can_delete = False
    readonly_fields = ("quantity_change", "movement_type", "reason", "created_by", "created_at")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock_quantity", "is_active", "is_featured")
    list_filter = ("category", "is_active", "is_featured")
    search_fields = ("name", "sku", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline, InventoryMovementInline]

    def save_model(self, request, obj, form, change):
        previous_stock = Product.objects.filter(pk=obj.pk).values_list("stock_quantity", flat=True).first() if change else 0
        super().save_model(request, obj, form, change)
        difference = obj.stock_quantity - (previous_stock or 0)
        if difference:
            InventoryMovement.objects.create(product=obj, quantity_change=difference, movement_type=InventoryMovement.MovementType.ADJUSTMENT, reason="Admin inventory update", created_by=request.user)


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity_change", "movement_type", "created_by", "created_at")
    list_filter = ("movement_type", "created_at")
    search_fields = ("product__name", "product__sku", "reason")
    readonly_fields = ("product", "quantity_change", "movement_type", "reason", "created_by", "created_at")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
