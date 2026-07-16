from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from products.models import Product, Category
from orders.models import OrderItem


def farmer_required(user):
    if not user.is_farmer:
        raise PermissionDenied("You must be a registered farmer to access this page.")


@login_required
def farmer_dashboard(request):
    farmer_required(request.user)
    products = Product.objects.filter(farmer=request.user)
    sold_items = OrderItem.objects.filter(product__farmer=request.user)
    total_sales = sum(item.total for item in sold_items)
    total_units_sold = sum(item.quantity for item in sold_items)

    return render(request, 'farmers/dashboard.html', {
        'products': products,
        'total_sales': total_sales,
        'total_units_sold': total_units_sold,
        'product_count': products.count(),
    })


@login_required
def farmer_product_add(request):
    farmer_required(request.user)
    categories = Category.objects.all()

    if request.method == 'POST':
        Product.objects.create(
            farmer=request.user,
            category_id=request.POST.get('category'),
            name=request.POST.get('name'),
            description=request.POST.get('description'),
            price=request.POST.get('price'),
            old_price=request.POST.get('old_price') or None,
            unit=request.POST.get('unit'),
            stock=request.POST.get('stock'),
            image_url=request.POST.get('image_url'),
            is_organic=request.POST.get('is_organic') == 'on',
            is_active=True,
        )
        messages.success(request, 'Product added successfully.')
        return redirect('farmer_dashboard')

    return render(request, 'farmers/product_form.html', {'categories': categories, 'product': None})


@login_required
def farmer_product_edit(request, product_id):
    farmer_required(request.user)
    product = get_object_or_404(Product, id=product_id, farmer=request.user)
    categories = Category.objects.all()

    if request.method == 'POST':
        product.category_id = request.POST.get('category')
        product.name = request.POST.get('name')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.old_price = request.POST.get('old_price') or None
        product.unit = request.POST.get('unit')
        product.stock = request.POST.get('stock')
        product.image_url = request.POST.get('image_url')
        product.is_organic = request.POST.get('is_organic') == 'on'
        product.is_active = request.POST.get('is_active') == 'on'
        product.save()
        messages.success(request, 'Product updated.')
        return redirect('farmer_dashboard')

    return render(request, 'farmers/product_form.html', {'categories': categories, 'product': product})


@login_required
def farmer_product_delete(request, product_id):
    farmer_required(request.user)
    product = get_object_or_404(Product, id=product_id, farmer=request.user)
    product.delete()
    messages.info(request, 'Product deleted.')
    return redirect('farmer_dashboard')