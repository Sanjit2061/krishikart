from django.urls import path
from . import views

urlpatterns = [
    path('farmer/dashboard/', views.farmer_dashboard, name='farmer_dashboard'),
    path('farmer/products/add/', views.farmer_product_add, name='farmer_product_add'),
    path('farmer/products/<int:product_id>/edit/', views.farmer_product_edit, name='farmer_product_edit'),
    path('farmer/products/<int:product_id>/delete/', views.farmer_product_delete, name='farmer_product_delete'),
]