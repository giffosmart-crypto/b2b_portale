from django.urls import path
from . import views

app_name = "partners"

urlpatterns = [
    # Dashboard partner
    path("dashboard/", views.partner_dashboard, name="dashboard"),
    path("analytics/", views.partner_analytics, name="analytics"),
    path("commissions/", views.partner_commissions, name="commissions"),
    path("partner/commissions/", views.partner_commissions, name="commissions"),

    # Ordini partner
    path("orders/", views.partner_order_list, name="order_list"),
    path("orders/archive/", views.partner_order_archive, name="order_archive"),
    path("orders/<int:order_id>/", views.partner_order_detail, name="order_detail"),

    # Export ordini partner
    path("orders/export/csv/", views.partner_order_export_csv, name="order_export_csv"),
    path("orders/export/xlsx/", views.partner_order_export_xlsx, name="order_export_xlsx"),

    # Aggiornamento stato singola riga d’ordine
    path(
        "orders/item/<int:item_id>/status/",
        views.partner_update_item_status,
        name="update_item_status",
    ),

    # PROFILO PARTNER
    path("profile/", views.partner_profile, name="profile"),

    # ==========================================================
    #   🆕 GESTIONE PRODOTTI PARTNER (catalogo proprio)
    # ==========================================================

    # Lista prodotti
    path("products/", views.partner_product_list, name="product_list"),

    # Crea prodotto
    path("products/add/", views.partner_product_create, name="product_create"),

    # Modifica prodotto
    path("products/<int:product_id>/edit/", views.partner_product_edit, name="product_edit"),

    # ==========================================================
    #   🆕 NOTIFICHE PARTNER
    # ==========================================================

    path("notifications/", views.partner_notification_list, name="notifications"),
]
