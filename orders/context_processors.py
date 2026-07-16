from .models import Cart

def cart_context(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return {'nav_cart_count': cart.item_count}
    return {'nav_cart_count': 0}