# b2b_portale/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render

# Home pubblica + redirect post-login
from cms.views import HomeView


# NOTA:
# La home pubblica è gestita da cms.views.HomeView, che effettua anche il
# redirect automatico degli utenti autenticati verso la loro area riservata.


# --- CONTACT VIEW ---
def contact(request):
    return render(request, "contact.html")


urlpatterns = [

    # 🏠 HOME PAGE
    path("", HomeView.as_view(), name="home"),

    # 📩 CONTATTI
    path("contatti/", contact, name="contact"),

    # Admin Django
    path("admin/", admin.site.urls),

    # 🔐 Admin Panel (nuova area backoffice)
    path("admin-panel/", include(("backoffice.urls", "backoffice"), namespace="backoffice")),

    # Catalogo (ora sotto /catalog/)
    path("catalog/", include(("catalog.urls", "catalog"), namespace="catalog")),

    # Ordini
    path("orders/", include(("orders.urls", "orders"), namespace="orders")),

    # Accounts
    path("", include(("accounts.urls", "accounts"), namespace="accounts")),

    # Partner
    path("partner/", include(("partners.urls", "partners"), namespace="partners")),

    # CMS
    path("", include("cms.urls")),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
