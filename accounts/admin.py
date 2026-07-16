from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('phone', 'address', 'is_farmer')}),
    )
    list_display = ('username', 'email', 'is_farmer', 'is_staff')

admin.site.register(User, CustomUserAdmin)