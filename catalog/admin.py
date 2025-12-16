from django.contrib import admin
from django.utils import timezone
from .models import (
    Category,
    Product,
    KitComponent,
    ProductImage,
    ProductAvailability,
    ProductRating,
)

class KitComponentInline(admin.TabularInline):
    model = KitComponent
    extra = 1

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


# ----------------------------
# Category Admin
# ----------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


# ----------------------------
# Product Admin
# ----------------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "supplier",
        "category",
        "base_price",
        "partner_commission_rate",  # 👈 visibile subito in lista
        "is_active",
    )
    list_filter = ("supplier", "category", "is_active")
    search_fields = (
        "name",
        "supplier__company_name",
        "category__name",
        "short_description",
    )
    autocomplete_fields = ("supplier", "category")
    prepopulated_fields = {"slug": ("name",)}

    fieldsets = (
        (
            "Informazioni prodotto",
            {
                "fields": (
                    "name",
                    "slug",
                    "supplier",
                    "category",
                    "short_description",
                    "description",
                    "is_active",
                )
            },
        ),
        (
            "Prezzi e commissioni",
            {
                "fields": (
                    "base_price",
                    "partner_commission_rate",  # 👈 editabile in modo chiaro
                )
            },
        ),
    )


# ----------------------------
# Product Availability Admin
# ----------------------------
@admin.register(ProductAvailability)
class ProductAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("product", "date", "available_quantity")
    list_filter = ("product", "date")
    search_fields = ("product__name",)


# ======================================================
# ✅ ProductRating Admin – Moderazione Recensioni
# ======================================================
@admin.register(ProductRating)
class ProductRatingAdmin(admin.ModelAdmin):

    list_display = (
        "product",
        "user",
        "rating",
        "short_comment",
        "created_at",
        "moderation_status",
        "is_approved",
        "moderated_by",
        "moderated_at",
        "supplier",
    )

    list_filter = (
        "moderation_status",
        "is_approved",
        "rating",
        "created_at",
        "product",
        ("product__supplier", admin.RelatedOnlyFieldListFilter),
        "moderated_by",
    )

    search_fields = (
        "product__name",
        "user__email",
        "user__first_name",
        "user__last_name",
        "comment",
    )

    ordering = ("-created_at",)

    actions = ["approve_reviews", "reject_reviews"]

    def supplier(self, obj):
        return obj.product.supplier
    supplier.short_description = "Partner"

    def short_comment(self, obj):
        if not obj.comment:
            return ""
        return obj.comment[:60] + ("..." if len(obj.comment) > 60 else "")
    short_comment.short_description = "Commento"

    # --- Azioni di massa con audit ---

    def approve_reviews(self, request, queryset):
        """
        Segna le recensioni come APPROVATE e registra chi/ quando.
        """
        now = timezone.now()
        count = 0
        for r in queryset:
            r.is_approved = True
            r.moderation_status = ProductRating.STATUS_APPROVED
            r.moderated_by = request.user
            r.moderated_at = now
            r.save(update_fields=["is_approved", "moderation_status", "moderated_by", "moderated_at"])
            count += 1
        self.message_user(request, f"{count} recensioni APPROVATE.")
    approve_reviews.short_description = "Approva recensioni selezionate"

    def reject_reviews(self, request, queryset):
        """
        Segna le recensioni come RIFIUTATE e registra chi/ quando.
        """
        now = timezone.now()
        count = 0
        for r in queryset:
            r.is_approved = False
            r.moderation_status = ProductRating.STATUS_REJECTED
            r.moderated_by = request.user
            r.moderated_at = now
            r.save(update_fields=["is_approved", "moderation_status", "moderated_by", "moderated_at"])
            count += 1
        self.message_user(request, f"{count} recensioni RIFIUTATE.")
    reject_reviews.short_description = "Rifiuta recensioni selezionate"
