import os
import uuid
from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

from products.models import Product
from admin_dashboard.models import Offer
from payments.models import Payment
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

    pending_payment_order = None
    if cart.items.count() == 0:
        pending_payment_order = Order.objects.filter(
            user=request.user, payment_method='esewa', payment_status='pending'
        ).order_by('-created_at').first()

    coupon_code = request.session.get('coupon_code')
    discount_percent = Decimal(str(request.session.get('coupon_discount', 0)))
    discount_amount = (cart.total * discount_percent / 100) if discount_percent else Decimal('0')
    final_total = cart.total - discount_amount

    user_order_count = Order.objects.filter(user=request.user).exclude(status='cancelled').count()
    today = timezone.now().date()
    active_offers = Offer.objects.filter(is_active=True, valid_from__lte=today, valid_until__gte=today)

    return render(request, 'orders/cart.html', {
        'cart': cart,
        'pending_payment_order': pending_payment_order,
        'coupon_code': coupon_code,
        'discount_amount': discount_amount,
        'final_total': final_total,
        'is_first_time_customer': user_order_count == 0,
        'active_offers': active_offers,
    })


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

        if payment_method == 'esewa' and final_total <= 0:
            messages.error(request, 'Your order total is Rs 0 due to the applied coupon. Please use Cash on Delivery for fully-discounted orders.')
            return redirect('checkout')

        # If there's already an unpaid eSewa order pending, resume it instead of duplicating —
        # but only if it's actually payable. A stale Rs 0 pending order (e.g. left over
        # from an earlier fully-discounted attempt) must not be sent to eSewa.
        if payment_method == 'esewa':
            existing_pending = Order.objects.filter(
                user=request.user, payment_method='esewa', payment_status='pending'
            ).order_by('-created_at').first()
            if existing_pending:
                if existing_pending.total_amount and existing_pending.total_amount > 0:
                    return redirect('esewa_initiate', order_number=existing_pending.order_number)
                existing_pending.status = 'cancelled'
                existing_pending.payment_status = 'cancelled'
                existing_pending.save()

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

        if payment_method == 'cod':
            # COD is guaranteed, so clear cart and reduce stock immediately
            for item in cart.items.all():
                item.product.stock -= item.quantity
                item.product.save()
            cart.items.all().delete()
            request.session.pop('coupon_code', None)
            request.session.pop('coupon_discount', None)
            return redirect('order_success', order_number=order.order_number)

        # For eSewa: DO NOT clear cart or reduce stock yet — only after payment confirms
        return redirect('esewa_initiate', order_number=order.order_number)

    return render(request, 'orders/checkout.html', {
        'cart': cart,
        'coupon_code': coupon_code,
        'discount_amount': discount_amount,
        'final_total': final_total,
    })


@login_required
def order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    payment = Payment.objects.filter(order=order).first()

    if order.payment_method == 'esewa':
        session_key = f'order_confirmed_{order.order_number}'
        if request.session.get(session_key):
            messages.info(request, 'Payment already completed for this order. Redirecting you to the homepage.')
            return redirect('home')
        request.session[session_key] = True

    return render(request, 'orders/order_success.html', {'order': order, 'payment': payment})

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})


@login_required
def download_receipt(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    payment = Payment.objects.filter(order=order).first()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], alignment=TA_CENTER, textColor=colors.HexColor('#2E7D32'))
    elements.append(Paragraph("KrishiKart — Payment Receipt", title_style))
    elements.append(Spacer(1, 10))

    # Embed the local black/dark eSewa logo (the site's own logo is a white-text
    # variant meant for a dark navbar, which is invisible on a white PDF page —
    # so we use our own local asset instead of fetching a remote one).
    esewa_logo_dir = os.path.join(settings.BASE_DIR, 'static', 'images')
    esewa_logo_path = None
    for filename in ('esewa_logo_black.png', 'esewa_logo_black.webp'):
        candidate = os.path.join(esewa_logo_dir, filename)
        if os.path.exists(candidate):
            esewa_logo_path = candidate
            break

    if esewa_logo_path:
        logo_img = Image(esewa_logo_path, width=100, height=30)
        logo_table = Table([[logo_img]], colWidths=[110])
        logo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F5F5F5')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        esewa_logo = logo_table
    else:
        esewa_logo = Paragraph("eSewa", styles['Normal'])

    elements.append(esewa_logo)
    elements.append(Spacer(1, 15))

    data = [
        ["Order Number", order.order_number],
        ["Order Date", order.created_at.strftime('%b %d, %Y at %I:%M %p')],
        ["Customer", order.user.username],
        ["Delivery Address", order.shipping_address or "-"],
        ["Payment Method", order.payment_method.upper()],
        ["Order Status", order.get_status_display()],
    ]

    if payment:
        data += [
            ["Reference Unique ID", payment.transaction_uuid],
            ["Transaction Code", payment.esewa_ref_id or "-"],
            ["Payment Status", payment.status.upper()],
            ["Paid On", payment.created_at.strftime('%b %d, %Y at %I:%M %p')],
        ]

    table = Table(data, colWidths=[150, 300])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F5E9')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1B5E20')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#C8E6C9')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    # Order items table
    items_data = [["Product", "Qty", "Price", "Total"]]
    for item in order.items.all():
        items_data.append([item.product_name, str(item.quantity), f"Rs {item.price}", f"Rs {item.total}"])
    items_data.append(["", "", "Grand Total", f"Rs {order.total_amount}"])

    items_table = Table(items_data, colWidths=[200, 60, 90, 100])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(Paragraph("Order Items", styles['Heading3']))
    elements.append(Spacer(1, 8))
    elements.append(items_table)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Thank you for shopping with KrishiKart — Fresh from Farm to your Home", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="KrishiKart_Receipt_{order.order_number}.pdf"'
    return response

@login_required
def order_statement(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    payment = Payment.objects.filter(order=order).first()
    return render(request, 'orders/order_statement.html', {'order': order, 'payment': payment})

@login_required
def cancel_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user, payment_status='pending')
    order.status = 'cancelled'
    order.payment_status = 'cancelled'
    order.save()
    messages.info(request, 'Order cancelled. You can start a fresh checkout anytime.')
    return redirect('view_cart')