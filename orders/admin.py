from django.contrib import admin
from .models import Order, OrderItem, PartnerPayout


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "partner", "quantity", "unit_price", "total_price")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "structure", "status", "total", "created_at")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("client__username", "structure__name")
    inlines = [OrderItemInline]
    

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "product",
        "partner",
        "quantity",
        "unit_price",
        "total_price",
        "commission_rate",
        "commission_amount",
        "partner_status",
        "is_liquidated"
    )
    list_filter = ("partner", "partner_status", "is_liquidated")
    search_fields = ("order__id", "product__name", "partner__company_name")


@admin.register(PartnerPayout)
class PartnerPayoutAdmin(admin.ModelAdmin):
    list_display = (
        "partner",
        "period_start",
        "period_end",
        "total_commission",
        "status",
        "paid_at",
    )
    list_filter = ("status", "period_start", "period_end", "partner")
    search_fields = ("partner__company_name",)
    date_hierarchy = "period_end"

    actions = ["mark_as_paid", "mark_as_confirmed"]

    def mark_as_paid(self, request, queryset):
        from django.utils import timezone

        updated = queryset.update(
            status=PartnerPayout.STATUS_PAID,
            paid_at=timezone.now(),
        )
        self.message_user(request, f"{updated} payout segnati come PAGATI.")

    mark_as_paid.short_description = "Segna come PAGATI i payout selezionati"

    def mark_as_confirmed(self, request, queryset):
        updated = queryset.update(status=PartnerPayout.STATUS_CONFIRMED)
        self.message_user(request, f"{updated} payout segnati come CONFERMATI.")

    mark_as_confirmed.short_description = "Segna come CONFERMATI i payout selezionati"
