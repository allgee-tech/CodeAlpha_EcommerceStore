import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cart.models import Cart
from cart.services import database_lines, snapshot_count, snapshot_total
from .forms import CheckoutForm
from .models import Order
from .services import OrderProcessingError, cancel_order, delivery_fee, place_order

@login_required
def checkout(request):
    cart = Cart.objects.filter(user=request.user).first()
    lines = database_lines(cart) if cart else []
    token = request.POST.get("checkout_token") if request.method == "POST" else str(uuid.uuid4())
    form = CheckoutForm(request.POST or None, user=request.user, initial={"checkout_token": token})
    if request.method == "POST" and form.is_valid():
        try:
            order, created = place_order(request.user, form.cleaned_data)
        except OrderProcessingError as error:
            messages.error(request, str(error))
        else:
            if created:
                messages.success(request, f"Order {order.reference} placed successfully.")
            return redirect("orders:confirmation", reference=order.reference)
    subtotal = snapshot_total(lines)
    fee = delivery_fee(country=form.data.get("country") or form.initial.get("country", "Ghana"))
    return render(request, "orders/checkout.html", {"form": form, "cart_lines": lines, "cart_subtotal": subtotal, "delivery_fee": fee, "order_total": subtotal + fee, "cart_item_count": snapshot_count(lines)})

@login_required
def order_list(request):
    orders = request.user.orders.prefetch_related("items").all()
    return render(request, "orders/list.html", {"orders": orders})

@login_required
def order_detail(request, reference):
    order = get_object_or_404(Order.objects.prefetch_related("items__product"), reference=reference, user=request.user)
    return render(request, "orders/detail.html", {"order": order})

@login_required
def confirmation(request, reference):
    order = get_object_or_404(Order.objects.prefetch_related("items__product"), reference=reference, user=request.user)
    return render(request, "orders/confirmation.html", {"order": order})

@require_POST
@login_required
def cancel(request, reference):
    order = get_object_or_404(Order, reference=reference, user=request.user)
    try:
        cancel_order(order.pk, request.user)
    except OrderProcessingError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Order {order.reference} has been cancelled and stock restored.")
    return redirect("orders:detail", reference=reference)
