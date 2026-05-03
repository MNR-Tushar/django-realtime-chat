from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'is_online', 'is_staff']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('avatar', 'bio', 'is_online')}),
    )