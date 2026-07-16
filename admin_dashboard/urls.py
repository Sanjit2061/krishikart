from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_home, name='dashboard_home'),
    path('dashboard/offers/', views.offer_list, name='offer_list'),
    path('dashboard/offers/add/', views.offer_add, name='offer_add'),
    path('dashboard/offers/<int:offer_id>/edit/', views.offer_edit, name='offer_edit'),
    path('dashboard/offers/<int:offer_id>/delete/', views.offer_delete, name='offer_delete'),
    path('dashboard/buyers/', views.buyer_list, name='buyer_list'),
    path('dashboard/orders/', views.order_list, name='order_list'),
    path('dashboard/orders/<int:order_id>/update/', views.order_update_status, name='order_update_status'),
    path('dashboard/chart-data/', views.chart_data, name='chart_data'),
]