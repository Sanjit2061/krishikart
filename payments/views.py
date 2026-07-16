import hmac
import hashlib
import base64
import json
import uuid
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from orders.models import Order
from .models import Payment


def generate_esewa_signature(total_amount, transaction_uuid, product_code):
    message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    key = settings.ESEWA_SECRET_KEY.encode('utf-8')
    hash_bytes = hmac.new(key, message.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(hash_bytes).decode('utf-8')


@login_required
def esewa_initiate(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    transaction_uuid = f"{order.order_number}-{uuid.uuid4().hex[:8]}"
    total_amount = str(order.total_amount)

    signature = generate_esewa_signature(total_amount, transaction_uuid, settings.ESEWA_MERCHANT_CODE)

    Payment.objects.update_or_create(
        order=order,
        defaults={
            'user': request.user,
            'amount': order.total_amount,
            'transaction_uuid': transaction_uuid,
            'status': 'pending',
        }
    )

    context = {
        'order': order,
        'total_amount': total_amount,
        'transaction_uuid': transaction_uuid,
        'product_code': settings.ESEWA_MERCHANT_CODE,
        'signature': signature,
        'esewa_url': settings.ESEWA_PAYMENT_URL,
        'success_url': f"{settings.SITE_URL}/payments/esewa/success/",
        'failure_url': f"{settings.SITE_URL}/payments/esewa/failure/",
    }
    return render(request, 'payments/esewa_redirect.html', context)


def esewa_success(request):
    encoded_data = request.GET.get('data')
    if not encoded_data:
        messages.error(request, 'Invalid payment response.')
        return redirect('home')

    try:
        decoded_bytes = base64.b64decode(encoded_data)
        response_data = json.loads(decoded_bytes)
    except Exception:
        messages.error(request, 'Could not verify payment response.')
        return redirect('home')

    transaction_uuid = response_data.get('transaction_uuid')
    status = response_data.get('status')
    ref_id = response_data.get('transaction_code')

    try:
        payment = Payment.objects.get(transaction_uuid=transaction_uuid)
    except Payment.DoesNotExist:
        messages.error(request, 'Payment record not found.')
        return redirect('home')

    if status == 'COMPLETE':
        payment.status = 'complete'
        payment.esewa_ref_id = ref_id
        payment.save()

        order = payment.order
        order.payment_status = 'paid'
        order.status = 'paid'
        order.save()

        messages.success(request, 'Payment successful via eSewa!')
        return redirect('order_success', order_number=order.order_number)
    else:
        payment.status = 'failed'
        payment.save()
        messages.error(request, 'Payment was not completed.')
        return redirect('view_cart')


def esewa_failure(request):
    messages.error(request, 'Payment was cancelled or failed. Please try again.')
    return redirect('view_cart')