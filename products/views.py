from django.shortcuts import redirect, render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Product, Category


from django.contrib import messages
from .models import NewsletterSubscriber

def subscribe_newsletter(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email:
            obj, created = NewsletterSubscriber.objects.get_or_create(email=email)
            if created:
                messages.success(request, "You're subscribed! Expect weekly harvest updates and exclusive discount codes in your inbox soon.")
            else:
                messages.info(request, "You're already subscribed — more updates coming your way soon!")
    return redirect(request.META.get('HTTP_REFERER', 'home'))


def home(request):
    products = Product.objects.filter(is_active=True, is_featured=True)[:8]
    categories = Category.objects.all()
    return render(request, 'home.html', {
        'products': products,
        'categories': categories
    })


def product_list(request):
    category_slug = request.GET.get('category')
    query = request.GET.get('q', '').strip()

    products = Product.objects.filter(is_active=True)

    if category_slug:
        products = products.filter(category__slug=category_slug)

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    paginator = Paginator(products.order_by('-created_at'), 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()
    return render(request, 'products/list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'selected_category': category_slug,
        'query': query,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    related_products = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(id=product.id)[:4]
    return render(request, 'products/detail.html', {
        'product': product,
        'related_products': related_products,
    })

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')

def privacy_policy(request):
    return render(request, 'privacy_policy.html')

def terms_of_service(request):
    return render(request, 'terms_of_service.html')