from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import Cart
from .services import CartValidationError, add_product, clear_cart, database_lines, guest_lines, remove_item, snapshot_count, snapshot_total, update_product_quantity


def detail(request):
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        lines = database_lines(cart) if cart else []
    else:
        cart = None
        lines = guest_lines(request.session)
    return render(request, "cart/detail.html", {"cart": cart, "cart_lines": lines, "cart_subtotal": snapshot_total(lines), "cart_item_count": snapshot_count(lines)})


@require_POST
def add(request, product_id):
    try:
        product = add_product(request.user, request.session, product_id, request.POST.get("quantity", 1))
    except CartValidationError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"{product.name} added to your bag.")
    return redirect(request.POST.get("next") or "cart:detail")


@require_POST
def update(request, item_id):
    try:
        product = update_product_quantity(request.user, request.session, item_id, request.POST.get("quantity"))
    except CartValidationError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"{product.name} quantity updated.")
    return redirect("cart:detail")


@require_POST
def remove(request, item_id):
    remove_item(request.user, request.session, item_id)
    messages.success(request, "Item removed from your bag.")
    return redirect("cart:detail")


@require_POST
def clear(request):
    clear_cart(request.user, request.session)
    messages.success(request, "Your bag has been cleared.")
    return redirect("cart:detail")
