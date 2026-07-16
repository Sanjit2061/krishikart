from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

from accounts.models import User
from orders.models import Order, OrderItem
from .models import Offer


@staff_member_required
def dashboard_home(request):
    total_revenue = Order.objects.filter(payment_status__in=['paid']).aggregate(total=Sum('total_amount'))['total'] or 0
    total_orders = Order.objects.count()
    total_customers = User.objects.filter(is_farmer=False, is_staff=False).count()
    total_farmers = User.objects.filter(is_farmer=True).count()

    thirty_days_ago = timezone.now() - timedelta(days=30)
    active_users = User.objects.filter(last_login__gte=thirty_days_ago).count()

    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:8]
    active_offers = Offer.objects.filter(is_active=True).count()

    context = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'total_customers': total_customers,
        'total_farmers': total_farmers,
        'active_users': active_users,
        'recent_orders': recent_orders,
        'active_offers': active_offers,
    }
    return render(request, 'admin_dashboard/dashboard.html', context)


@staff_member_required
def chart_data(request):
    today = timezone.now().date()
    labels = []
    revenue_data = []
    order_counts = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_orders = Order.objects.filter(created_at__date=day)
        labels.append(day.strftime('%b %d'))
        revenue_data.append(float(day_orders.filter(payment_status='paid').aggregate(total=Sum('total_amount'))['total'] or 0))
        order_counts.append(day_orders.count())

    top_products = (OrderItem.objects
                     .values('product_name')
                     .annotate(total_sold=Sum('quantity'))
                     .order_by('-total_sold')[:5])

    status_breakdown = (Order.objects
                        .values('status')
                        .annotate(count=Count('id')))

    return JsonResponse({
        'labels': labels,
        'revenue_data': revenue_data,
        'order_counts': order_counts,
        'top_products': list(top_products),
        'status_breakdown': list(status_breakdown),
    })


@staff_member_required
def buyer_list(request):
    customers = (User.objects
                 .filter(is_farmer=False, is_staff=False)
                 .annotate(order_count=Count('order'), total_spent=Sum('order__total_amount'))
                 .order_by('-total_spent'))
    return render(request, 'admin_dashboard/buyers.html', {'customers': customers})


@staff_member_required
def order_list(request):
    orders = Order.objects.select_related('user').order_by('-created_at')
    return render(request, 'admin_dashboard/order_list.html', {'orders': orders})


@staff_member_required
def order_update_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        order.status = request.POST.get('status')
        order.save()
        messages.success(request, f'Order #{order.order_number} updated to {order.get_status_display()}.')
    return redirect('order_list')


@staff_member_required
def offer_list(request):
    offers = Offer.objects.all().order_by('-created_at')
    return render(request, 'admin_dashboard/offers.html', {'offers': offers})


@staff_member_required
def offer_add(request):
    if request.method == 'POST':
        Offer.objects.create(
            title=request.POST.get('title'),
            code=request.POST.get('code').upper(),
            discount_percent=request.POST.get('discount_percent'),
            description=request.POST.get('description', ''),
            valid_from=request.POST.get('valid_from'),
            valid_until=request.POST.get('valid_until'),
            is_active=request.POST.get('is_active') == 'on',
        )
        messages.success(request, 'Offer created successfully.')
        return redirect('offer_list')
    return render(request, 'admin_dashboard/offer_form.html', {'offer': None})


@staff_member_required
def offer_edit(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)
    if request.method == 'POST':
        offer.title = request.POST.get('title')
        offer.code = request.POST.get('code').upper()
        offer.discount_percent = request.POST.get('discount_percent')
        offer.description = request.POST.get('description', '')
        offer.valid_from = request.POST.get('valid_from')
        offer.valid_until = request.POST.get('valid_until')
        offer.is_active = request.POST.get('is_active') == 'on'
        offer.save()
        messages.success(request, 'Offer updated successfully.')
        return redirect('offer_list')
    return render(request, 'admin_dashboard/offer_form.html', {'offer': offer})


@staff_member_required
def offer_delete(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)
    offer.delete()
    messages.info(request, 'Offer deleted.')
    return redirect('offer_list')