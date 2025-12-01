from django.contrib import admin
from .models import PartnerProfile


@admin.register(PartnerProfile)
class PartnerProfileAdmin(admin.ModelAdmin):
    list_display = ("company_name", "vat_number", "phone", "is_active")
    search_fields = ("company_name", "vat_number")
    list_filter = ("is_active",)
