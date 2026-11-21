from .models import Cart
from .services import database_lines, guest_lines, snapshot_count, snapshot_total

def cart_summary(request):
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        lines = database_lines(cart) if cart else []
    else:
        lines = guest_lines(request.session)
    return {"cart_count": snapshot_count(lines), "cart_subtotal": snapshot_total(lines)}

