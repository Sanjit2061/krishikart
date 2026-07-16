from django.urls import path
from . import views

urlpatterns = [
    path('esewa/initiate/<str:order_number>/', views.esewa_initiate, name='esewa_initiate'),
    path('esewa/success/', views.esewa_success, name='esewa_success'),
    path('esewa/failure/', views.esewa_failure, name='esewa_failure'),
]