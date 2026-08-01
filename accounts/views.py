from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from .models import User

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid credentials')
    return render(request, 'accounts/login.html')

@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


@never_cache
def session_status(request):
    """Lightweight endpoint the client polls after back/forward navigation
    to check whether the real session is still authenticated, without
    forcing a full page reload every time."""
    return JsonResponse({'authenticated': request.user.is_authenticated})


def register_view(request):
    if request.user.is_authenticated:
        messages.info(request, 'You were logged out of your current account to register a new one.')
        logout(request)
        return redirect('register')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        is_farmer = request.POST.get('is_farmer') == 'on'

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
        else:
            user = User.objects.create_user(username=username, email=email, password=password, is_farmer=is_farmer)
            login(request, user)
            return redirect('home')
    return render(request, 'accounts/register.html')