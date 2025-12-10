from django.urls import path
from . import views

app_name = "backoffice"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path(
        "dashboard/live-stats/",
        views.dashboard_live_stats,
        name="dashboard_live_stats",
    ),

    # ORDINI
    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),

    # PARTNER
    path("partners/", views.partner_list, name="partner_list"),

    # CLIENTI
    path("clients/", views.client_list, name="client_list"),

    # STRUTTURE CLIENTE
    path("client-structures/", views.client_structure_list, name="client_structure_list"),
    path("client-structures/<int:pk>/", views.client_structure_detail, name="client_structure_detail"),

    # PRODOTTI
    path("products/", views.product_list, name="product_list"),

    # KIT
    path("kits/", views.kit_list, name="kit_list"),

    # CATEGORIE PRODOTTO
    path("categories/", views.category_list, name="category_list"),

    # PAGINE CMS
    path("pages/", views.cms_page_list, name="cms_page_list"),

    # REPORT COMMISSIONI (portale + partner)
    path(
        "commission-report/",
        views.commission_report,
        name="commission_report",
    ),
    path(
        "commission-report/export-csv/",
        views.commission_report_export_csv,
        name="commission_report_export_csv",
    ),
    path(
        "commission-report/export-xlsx/",
        views.commission_report_export_xlsx,
        name="commission_report_export_xlsx",
    ),
    path(
        "commission-report/export-pdf/",
        views.commission_report_export_pdf,
        name="commission_report_export_pdf",
    ),
    path(
        "commission-report/partner/<int:partner_id>/export-pdf/",
        views.commission_partner_pdf,
        name="commission_partner_pdf",
    ),
    
    path(
        "commission-report/detail/",
        views.commission_report_detail,
        name="commission_report_detail",
    ),
    # UTENTI COMPLETI
    path("users/", views.user_list, name="user_list"),

    # COMMISSIONI PARTNER
    path(
        "partner-commissions/",
        views.partner_commission_list,
        name="partner_commission_list",
    ),
    path(
        "partner-commissions/export/",
        views.partner_commission_export_csv,
        name="partner_commission_export_csv",
    ),
    path(
        "partner-commissions/<int:partner_id>/create-payout/",
        views.partner_payout_create,
        name="partner_payout_create",
    ),
    path(
        "partner-commissions/unliquidated/",
        views.unliquidated_commission_list,
        name="unliquidated_commission_list",
    ),
    path(
        "partner-commissions/liquidated/",
        views.liquidated_commission_list,
        name="liquidated_commission_list",
    ),

# ELENCO PAYOUT
    path(
        "partner-payouts/",
        views.partner_payout_list,
        name="partner_payout_list",
    ),

# ELENCO PAYOUT
    path(
        "partner-payouts/",
        views.partner_payout_list,
        name="partner_payout_list",
    ),

    # RECENSIONI PRODOTTI (BACKOFFICE)
    path("reviews/", views.review_list, name="review_list"),
    path("reviews/<int:pk>/", views.review_detail, name="review_detail"),
    path("reviews/<int:pk>/approve/", views.review_approve, name="review_approve"),
    path("reviews/<int:pk>/reject/", views.review_reject, name="review_reject"),
    
]
