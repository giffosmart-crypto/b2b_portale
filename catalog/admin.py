from django.contrib import admin
from .models import Category, Product, KitComponent, ProductImage, ProductAvailability

class KitComponentInline(admin.TabularInline):
    model = KitComponent
    extra = 1

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "supplier", "base_price", "is_active")
    list_filter = ("category", "supplier", "is_active")
    search_fields = ("name", "short_description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [KitComponentInline, ProductImageInline]

@admin.register(ProductAvailability)
class ProductAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("product", "date", "available_quantity")
    list_filter = ("product", "date")
    search_fields = ("product__name",)


