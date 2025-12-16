from django.contrib import admin
from .models import PartnerProfile, PartnerCategoryCommission


@admin.register(PartnerProfile)
class PartnerProfileAdmin(admin.ModelAdmin):
    list_display = ("company_name", "vat_number", "phone", "is_active")
    search_fields = ("company_name", "vat_number")
    list_filter = ("is_active",)
    
    
@admin.register(PartnerCategoryCommission)
class PartnerCategoryCommissionAdmin(admin.ModelAdmin):
    list_display = ("partner", "category", "commission_rate")
    list_filter = ("partner", "category")
    search_fields = ("partner__company_name", "category__name")
    autocomplete_fields = ("partner", "category")
