from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, ClientStructure


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Informazioni aggiuntive", {
            "fields": ("role", "company_name", "vat_number"),
        }),
    )
    list_display = ("username", "email", "role", "company_name", "is_active")
    list_filter = ("role", "is_staff", "is_active")


@admin.register(ClientStructure)
class ClientStructureAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "city", "is_default_shipping")
    list_filter = ("city", "is_default_shipping")
    search_fields = ("name", "owner__username")
