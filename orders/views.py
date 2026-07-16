import uuid
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from products.models import Product
from admin_dashboard.models import Offer
from .models import Cart, CartItem, Order, OrderItem


def get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart = get_or_create_cart(request.user)

    if product.stock <= 0:
        messages.error(request, f'{product.name} is out of stock.')
        return redirect(request.META.get('HTTP_REFERER', 'home'))

    item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': 1})
    if not created:
        if item.quantity + 1 > product.stock:
            messages.warning(request, f'Only {product.stock} of {product.name} available.')
        else:
            item.quantity += 1
            item.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'cart_count': cart.item_count})

    messages.success(request, f'{product.name} added to cart.')
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def view_cart(request):
    cart = get_or_create_cart(request.user)
    return render(request, 'orders/cart.html', {'cart': cart})


@login_required
def update_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        if quantity <= 0:
            item.delete()
        elif quantity > item.product.stock:
            messages.warning(request, f'Only {item.product.stock} available.')
        else:
            item.quantity = quantity
            item.save()
    return redirect('view_cart')


@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    messages.info(request, 'Item removed from cart.')
    return redirect('view_cart')


@login_required
def apply_coupon(request):
    cart = get_or_create_cart(request.user)
    code = request.POST.get('coupon_code', '').strip().upper()
    today = timezone.now().date()

    try:
        offer = Offer.objects.get(code=code, is_active=True, valid_from__lte=today, valid_until__gte=today)
        request.session['coupon_code'] = offer.code
        request.session['coupon_discount'] = float(offer.discount_percent)
        messages.success(request, f'Coupon "{offer.code}" applied — {offer.discount_percent}% off!')
    except Offer.DoesNotExist:
        request.session.pop('coupon_code', None)
        request.session.pop('coupon_discount', None)
        messages.error(request, 'Invalid or expired coupon code.')

    return redirect('view_cart')


@login_required
def checkout(request):
    cart = get_or_create_cart(request.user)
    if cart.items.count() == 0:
        messages.warning(request, 'Your cart is empty.')
        return redirect('view_cart')

    coupon_code = request.session.get('coupon_code')
    discount_percent = Decimal(str(request.session.get('coupon_discount', 0)))
    discount_amount = (cart.total * discount_percent / 100) if discount_percent else Decimal('0')
    final_total = cart.total - discount_amount

    if request.method == 'POST':
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        payment_method = request.POST.get('payment_method', 'cod')

        for item in cart.items.all():
            if item.quantity > item.product.stock:
                messages.error(request, f'Not enough stock for {item.product.name}.')
                return redirect('view_cart')

        order = Order.objects.create(
            user=request.user,
            order_number=str(uuid.uuid4()).split('-')[0].upper(),
            total_amount=final_total,
            coupon_code=coupon_code,
            discount_amount=discount_amount,
            shipping_address=address,
            phone=phone,
            payment_method=payment_method,
            status='pending',
            payment_status='pending' if payment_method == 'esewa' else 'cod_pending',
        )

        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                product_name=item.product.name,
                quantity=item.quantity,
                price=item.product.price,
                total=item.subtotal,
            )
            item.product.stock -= item.quantity
            item.product.save()

        cart.items.all().delete()
        request.session.pop('coupon_code', None)
        request.session.pop('coupon_discount', None)

        if payment_method == 'esewa':
            return redirect('esewa_initiate', order_number=order.order_number)

        return redirect('order_success', order_number=order.order_number)

    return render(request, 'orders/checkout.html', {
        'cart': cart,
        'coupon_code': coupon_code,
        'discount_amount': discount_amount,
        'final_total': final_total,
    })


@login_required
def order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'orders/order_success.html', {'order': order})


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})