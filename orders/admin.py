from django.contrib import admin, messages
from .models import Order, OrderItem
from .services import OrderProcessingError, cancel_order


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "unit_price", "quantity")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "total", "status", "payment_status", "created_at")
    list_filter = ("status", "payment_status", "payment_method", "created_at")
    search_fields = ("reference", "user__username", "email", "full_name")
    readonly_fields = ("reference", "checkout_token", "subtotal", "delivery_fee", "total", "created_at", "updated_at", "cancelled_at", "cancelled_by")
    inlines = [OrderItemInline]
    actions = ("cancel_and_restore_stock",)

    @admin.action(description="Cancel selected orders and restore stock")
    def cancel_and_restore_stock(self, request, queryset):
        cancelled = 0
        for order in queryset:
            try:
                cancel_order(order.pk, request.user)
            except OrderProcessingError as error:
                self.message_user(request, f"{order.reference}: {error}", messages.WARNING)
            else:
                cancelled += 1
        if cancelled:
            self.message_user(request, f"Cancelled {cancelled} order(s) and restored stock.", messages.SUCCESS)
