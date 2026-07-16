from django.contrib import admin
from .models import Offer

@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'discount_percent', 'is_active', 'valid_from', 'valid_until')
    list_filter = ('is_active',)