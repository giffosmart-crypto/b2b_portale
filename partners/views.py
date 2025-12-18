from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.urls import reverse

from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta

import json
import csv
from io import BytesIO
from openpyxl import Workbook

from decimal import Decimal

from .models import PartnerProfile, PartnerNotification
from orders.models import Order, OrderItem, OrderItemStatusLog, OrderMessage, PartnerPayout
from django.core.exceptions import ValidationError

# Import dei form
from .forms import (
    PartnerUserForm,
    PartnerProfileForm,
    PartnerProductForm,  # 👈 aggiunto
)

# Import modello Product per la gestione catalogo partner
from catalog.models import Product


# ============================================================
#   UTILITIES
# ============================================================

def _get_partner_profile_or_403(user):
    """
    Restituisce il PartnerProfile collegato all'utente,
    oppure None se l'utente non è un partner attivo.
    """
    if not user.is_authenticated:
        return None

    try:
        profile = user.partner_profile
    except PartnerProfile.DoesNotExist:
        return None

    if not profile.is_active:
        return None

    return profile


def create_partner_notification(partner, title, message, url=""):
    """
    Crea una notifica per il partner.
    """
    return PartnerNotification.objects.create(
        partner=partner,
        title=title,
        message=message,
        url=url or "",
    )


# ============================================================
#   PROFILO PARTNER — NEW
# ============================================================

@login_required
def partner_profile(request):
    """
    Pagina PROFILO PARTNER:
    - permette di modificare i dati dell'utente (nome, cognome, email)
    - permette di modificare i dati aziendali del PartnerProfile
    """
    profile = _get_partner_profile_or_403(request.user)
    if profile is None:
        return HttpResponseForbidden("Non sei abilitato come partner.")

    user = request.user

    if request.method == "POST":
        user_form = PartnerUserForm(request.POST, instance=user)
        profile_form = PartnerProfileForm(request.POST, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profilo aggiornato correttamente.")
            return redirect("partners:profile")
    else:
        user_form = PartnerUserForm(instance=user)
        profile_form = PartnerProfileForm(instance=profile)

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "partner": profile,
    }
    return render(request, "partners/partner_profile.html", context)


# ============================================================
#   UPDATE STATO ITEM (con AUDIT LOG + NOTIFICA + EMAIL CLIENTE)
# ============================================================

@login_required
def partner_update_item_status(request, item_id):
    profile = _get_partner_profile_or_403(request.user)
    if profile is None:
        return HttpResponseForbidden("Non sei abilitato come partner.")

    item = get_object_or_404(OrderItem, id=item_id, partner=profile)

    if request.method == "POST":
        new_status = request.POST.get("partner_status")
        valid_statuses = dict(OrderItem.PARTNER_STATUS_CHOICES).keys()

        if item.payout_id is not None or item.is_liquidated:
            messages.error(
                request,
                "Non puoi modificare lo stato: questa riga è già stata liquidata (payout generato)."
            )
            return redirect("partners:order_detail", order_id=item.order.id)
        
        if new_status in valid_statuses and new_status != item.partner_status:
            old_status = item.partner_status

            # 🔹 CALCOLO COMMISSIONE
            # Se la riga passa a COMPLETATA, calcoliamo (o ricalcoliamo) la commissione.
            if new_status == OrderItem.PARTNER_STATUS_COMPLETED:
                # NON ricalcoliamo se già calcolata: la fissiamo una volta sola
                if item.commission_amount in (None, Decimal("0.00")):
                    item.calculate_commission()

            # Se la riga viene RIFIUTATA, azzeriamo la commissione
            if new_status == OrderItem.PARTNER_STATUS_REJECTED:
                item.commission_rate = Decimal("0.00")
                item.commission_amount = Decimal("0.00")

            # Aggiorno la riga
            item.partner_status = new_status
            item.save()

            # === AUDIT LOG ===
            OrderItemStatusLog.objects.create(
                order_item=item,
                old_status=old_status,
                new_status=new_status,
                changed_by=request.user,
            )

            # === NOTIFICA INTERNA PER IL PARTNER ===
            detail_url = reverse("partners:order_detail", args=[item.order.id])

            old_label = dict(OrderItem.PARTNER_STATUS_CHOICES).get(old_status, old_status)
            new_label = dict(OrderItem.PARTNER_STATUS_CHOICES).get(new_status, new_status)

            title = f"Stato aggiornato per riga #{item.id}"
            message = (
                f"Lo stato della riga #{item.id} dell'ordine #{item.order.id} "
                f"è passato da '{old_label}' a '{new_label}'."
            )
            create_partner_notification(
                partner=profile,
                title=title,
                message=message,
                url=detail_url,
            )

            # === EMAIL AL CLIENTE ===
            client = item.order.client
            client_email = getattr(client, "email", None)

            if client_email:
                from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)

                email_subject = f"Aggiornamento sul tuo ordine #{item.order.id}"
                email_body = (
                    f"Ciao {client.first_name or client.username},\n\n"
                    f"lo stato della riga del tuo ordine #{item.order.id} "
                    f"relativa al prodotto '{item.product.name}' è stato aggiornato.\n\n"
                    f"Stato precedente: {old_label}\n"
                    f"Nuovo stato: {new_label}\n\n"
                    f"Partner: {profile.company_name}\n\n"
                    f"Se hai dubbi puoi contattare il supporto o il partner.\n\n"
                    f"Grazie,\n"
                    f"Il team del portale B2B"
                )

                try:
                    send_mail(
                        subject=email_subject,
                        message=email_body,
                        from_email=from_email,
                        recipient_list=[client_email],
                        fail_silently=True,
                    )
                except Exception:
                    pass

            messages.success(request, "Stato della riga aggiornato correttamente.")
        else:
            messages.warning(request, "Nessuna modifica di stato effettuata.")

    return redirect("partners:order_detail", order_id=item.order.id)


# ============================================================
#   LISTA ORDINI PARTNER
# ============================================================

@login_required
def partner_order_list(request):
    partner = _get_partner_profile_or_403(request.user)
    if partner is None:
        return redirect("catalog:product_list")

    # ordini che hanno almeno una riga assegnata al partner
    orders = (
        Order.objects
        .filter(items__partner=partner)
        .distinct()
        .order_by("-created_at")
    )

    # calcolo badge nuovi messaggi per ogni ordine
    for o in orders:
        o.unread_messages = OrderMessage.objects.filter(
            order=o,
            is_read_by_partner=False,
        ).exists()

    context = {
        "partner": partner,
        "orders": orders,
    }
    return render(request, "partners/order_list.html", context)


# ============================================================
#   DETTAGLIO ORDINE PARTNER
# ============================================================


@login_required
def partner_order_detail(request, order_id):
    """
    Dettaglio ordine lato partner, con:
    - righe associate al partner
    - audit log stati
    - chat ordine (messaggi con il cliente)
    """
    partner = _get_partner_profile_or_403(request.user)
    if partner is None:
        return redirect("catalog:product_list")

    # queryset di ordini che hanno almeno una riga per questo partner
    qs = (
        Order.objects
        .filter(items__partner=partner)
        .distinct()  # evita duplicati se ci sono più righe per lo stesso ordine
        .select_related("client", "structure")
    )

    # recupero l'ordine, garantendo un solo record
    order = get_object_or_404(qs, id=order_id)

    # Righe d'ordine di questo partner
    items = (
        OrderItem.objects
        .filter(order=order, partner=partner)
        .select_related("product")
        .prefetch_related("status_logs")
    )

    # Gestione invio nuovo messaggio (POST)
    if request.method == "POST":
        text = (request.POST.get("message") or "").strip()
        if text:
            OrderMessage.objects.create(
                order=order,
                sender=request.user,
                sender_role=OrderMessage.ROLE_PARTNER,
                message=text,
                is_read_by_partner=True,   # lo sto inviando io partner
                is_read_by_client=False,   # il cliente non l'ha ancora letto
            )
            messages.success(request, "Messaggio inviato al cliente.")
            return redirect("partners:order_detail", order_id=order.id)
        else:
            messages.error(request, "Il messaggio non può essere vuoto.")

    # Messaggi legati all'ordine (cronologia)
    messages_qs = (
        OrderMessage.objects
        .filter(order=order)
        .select_related("sender")
        .order_by("created_at")
    )

    # Il partner ora li ha visti: segniamo come letti lato partner
    messages_qs.filter(is_read_by_partner=False).update(is_read_by_partner=True)

    context = {
        "partner": partner,
        "order": order,
        "items": items,
        "messages": messages_qs,
    }
    return render(request, "partners/partner_order_detail.html", context)


# ============================================================
#   DASHBOARD PARTNER (senza grafici, solo KPI e liste)
# ============================================================

@login_required
def partner_dashboard(request):
    """
    Dashboard partner:
    - KPI principali
    - ricavi del mese
    - prodotti più venduti
    - ultime righe assegnate
    - ultimi ordini
    - notifiche non lette

    (i grafici avanzati sono nella pagina dedicata 'Report & grafici')
    """
    if getattr(request.user, "role", None) != "partner":
        return redirect("catalog:product_list")

    profile = _get_partner_profile_or_403(request.user)
    if profile is None:
        return redirect("catalog:product_list")

    # Tutte le righe d'ordine del partner
    items = (
        OrderItem.objects
        .filter(partner=profile)
        .select_related("order", "product")
        .order_by("-order__created_at")
    )

    from django.db.models import Sum
    from django.utils import timezone

    now = timezone.now()

    # ------------------------------------------------------------
    # KPI
    # ------------------------------------------------------------
    kpi = {
        "pending": items.filter(partner_status=OrderItem.PARTNER_STATUS_PENDING).count(),
        "accepted": items.filter(partner_status=OrderItem.PARTNER_STATUS_ACCEPTED).count(),
        "in_progress": items.filter(partner_status=OrderItem.PARTNER_STATUS_IN_PROGRESS).count(),
        "shipped": items.filter(partner_status=OrderItem.PARTNER_STATUS_SHIPPED).count(),
        "completed": items.filter(partner_status=OrderItem.PARTNER_STATUS_COMPLETED).count(),
        "rejected": items.filter(partner_status=OrderItem.PARTNER_STATUS_REJECTED).count(),
    }

    # ------------------------------------------------------------
    # Ricavi del mese (valore numerico)
    # ------------------------------------------------------------
    revenue_month = (
        items.filter(order__created_at__year=now.year, order__created_at__month=now.month)
        .aggregate(total=Sum("total_price"))
        .get("total") or 0
    )

    # ------------------------------------------------------------
    # Prodotti più venduti (TOP 5)
    # ------------------------------------------------------------
    top_products = (
        items.values("product__name")
        .annotate(qty=Sum("quantity"))
        .order_by("-qty")[:5]
    )

    # Ultime 10 righe assegnate
    latest_items = items[:10]

    # Ultimi 5 ordini
    recent_orders = (
        Order.objects
        .filter(items__partner=profile)
        .distinct()
        .order_by("-created_at")[:5]
    )

    # Notifiche
    unread_notifications_count = PartnerNotification.objects.filter(
        partner=profile,
        is_read=False,
    ).count()

    latest_notifications = PartnerNotification.objects.filter(
        partner=profile
    ).order_by("-created_at")[:5]

    context = {
        "partner": profile,
        "kpi": kpi,
        "revenue_month": revenue_month,
        "top_products": top_products,
        "latest_items": latest_items,
        "recent_orders": recent_orders,
        "unread_notifications_count": unread_notifications_count,
        "latest_notifications": latest_notifications,
    }

    return render(request, "partners/dashboard.html", context)


# ============================================================
#   PAGINA REPORT & GRAFICI PARTNER
# ============================================================

@login_required
def partner_analytics(request):
    """
    Pagina dedicata ai report e grafici del partner:
    - andamento vendite per mese
    - andamento ordini per mese
    - distribuzione righe per stato
    con filtro periodo (ultimi 3 / 6 / 12 mesi).
    """
    if getattr(request.user, "role", None) != "partner":
        return redirect("catalog:product_list")

    profile = _get_partner_profile_or_403(request.user)
    if profile is None:
        return redirect("catalog:product_list")

    # -----------------------------
    # Filtro periodo (3 / 6 / 12 mesi)
    # -----------------------------
    period_param = request.GET.get("period", "6").strip()  # default 6 mesi
    valid_periods = {"3": 90, "6": 180, "12": 365}  # giorni approssimati

    if period_param not in valid_periods:
        period_param = "6"

    days_back = valid_periods[period_param]

    # Tutte le righe d'ordine del partner
    items = (
        OrderItem.objects
        .filter(partner=profile)
        .select_related("order", "product")
    )

    from django.db.models import Sum, Count
    from django.db.models.functions import TruncMonth
    from django.utils import timezone

    now = timezone.now()
    start_date = now - timedelta(days=days_back)

    # ------------------------------------------------------------
    # 1) Vendite per mese (somma total_price per mese)
    # ------------------------------------------------------------
    revenue_by_month_qs = (
        items.filter(order__created_at__gte=start_date)
        .annotate(month=TruncMonth("order__created_at"))
        .values("month")
        .annotate(total=Sum("total_price"))
        .order_by("month")
    )

    revenue_chart_labels = [
        row["month"].strftime("%m/%y") for row in revenue_by_month_qs if row["month"]
    ]
    revenue_chart_data = [
        float(row["total"] or 0) for row in revenue_by_month_qs
    ]

    # ------------------------------------------------------------
    # 2) Andamento ordini per mese (conteggio ordini distinti)
    # ------------------------------------------------------------
    orders_qs = (
        Order.objects
        .filter(items__partner=profile, created_at__gte=start_date)
        .distinct()
    )

    orders_by_month_qs = (
        orders_qs
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    orders_chart_labels = [
        row["month"].strftime("%m/%y") for row in orders_by_month_qs if row["month"]
    ]
    orders_chart_data = [
        row["count"] or 0 for row in orders_by_month_qs
    ]

    # ------------------------------------------------------------
    # 3) Performance stati (quante righe in ogni stato)
    # ------------------------------------------------------------
    kpi = {
        "pending": items.filter(partner_status=OrderItem.PARTNER_STATUS_PENDING).count(),
        "accepted": items.filter(partner_status=OrderItem.PARTNER_STATUS_ACCEPTED).count(),
        "in_progress": items.filter(partner_status=OrderItem.PARTNER_STATUS_IN_PROGRESS).count(),
        "shipped": items.filter(partner_status=OrderItem.PARTNER_STATUS_SHIPPED).count(),
        "completed": items.filter(partner_status=OrderItem.PARTNER_STATUS_COMPLETED).count(),
        "rejected": items.filter(partner_status=OrderItem.PARTNER_STATUS_REJECTED).count(),
    }

    status_chart_labels = [
        label for _, label in OrderItem.PARTNER_STATUS_CHOICES
    ]
    status_chart_data = [
        kpi["pending"],
        kpi["accepted"],
        kpi["in_progress"],
        kpi["shipped"],
        kpi["completed"],
        kpi["rejected"],
    ]

    # Serializzo in JSON per il template
    context = {
        "partner": profile,
        "current_period": period_param,  # "3", "6" o "12"

        "revenue_chart_labels": json.dumps(revenue_chart_labels),
        "revenue_chart_data": json.dumps(revenue_chart_data),
        "orders_chart_labels": json.dumps(orders_chart_labels),
        "orders_chart_data": json.dumps(orders_chart_data),
        "status_chart_labels": json.dumps(status_chart_labels),
        "status_chart_data": json.dumps(status_chart_data),
    }

    return render(request, "partners/partner_analytics.html", context)
    
    
@login_required
def partner_commissions(request):
    """
    Pagina riepilogo commissioni e pagamenti del partner.

    LATO PARTNER:
    - totale GUADAGNO MATURATO = somma di partner_earnings
      (cioè totale righe ordine meno commissione portale)
    - totale GUADAGNO GIA' PAGATO = somma dei payout in stato 'Pagato'
    - saldo da ricevere = maturato - pagato
    - elenco righe commissionate
    - elenco pagamenti registrati
    """
    profile = _get_partner_profile_or_403(request.user)
    if profile is None:
        return HttpResponseForbidden("Non sei abilitato come partner.")

    from django.db.models import Sum

    # Righe completate che generano GUADAGNO per il partner,
    # solo su ordini COMPLETI (stato 'completed')
    items = (
        OrderItem.objects
        .filter(
            partner=profile,
            partner_status=OrderItem.PARTNER_STATUS_COMPLETED,
            order__status=Order.STATUS_COMPLETED,
        )
        .select_related("order", "product")
        .order_by("-order__created_at")
    )

    # 🔹 Totale GUADAGNO partner maturato (NON la commissione del portale)
    totals = items.aggregate(
        total_partner=Sum("partner_earnings"),
        total_portal=Sum("commission_amount"),  # se vuoi usarlo altrove
    )
    total_commission_matured = totals.get("total_partner") or Decimal("0.00")

    # Pagamenti registrati per il partner
    payouts = (
        PartnerPayout.objects
        .filter(partner=profile)
        .order_by("-period_end", "-created_at")
    )

    # 🔹 Importo già PAGATO al partner
    total_payout_paid = (
        payouts.filter(status=PartnerPayout.STATUS_PAID)
        .aggregate(total=Sum("total_commission"))
        .get("total") or Decimal("0.00")
    )

    # 🔹 Saldo ancora da ricevere
    total_commission_unpaid = total_commission_matured - total_payout_paid
    if total_commission_unpaid < Decimal("0.00"):
        total_commission_unpaid = Decimal("0.00")

    context = {
        "partner": profile,
        "commission_items": items,
        "payouts": payouts,
        "total_commission_matured": total_commission_matured,
        "total_payout_paid": total_payout_paid,
        "total_commission_unpaid": total_commission_unpaid,
    }

    return render(request, "partners/commissions.html", context)

# ============================================================
#   🆕 LISTA NOTIFICHE PARTNER
# ============================================================

@login_required
def partner_notification_list(request):
    """
    Lista delle notifiche del partner.
    Aprendo la pagina le mostriamo con lo stato attuale,
    poi segniamo come lette quelle non lette.
    """
    profile = _get_partner_profile_or_403(request.user)
    if profile is None:
        return HttpResponseForbidden("Non sei abilitato come partner.")

    notifications = PartnerNotification.objects.filter(
        partner=profile
    ).order_by("-created_at")

    context = {
        "partner": profile,
        "notifications": notifications,
    }

    # 1) render della pagina con lo stato attuale (is_read True/False)
    response = render(request, "partners/notifications.html", context)

    # 2) dopo aver mostrato la pagina, segniamo come lette le non lette
    PartnerNotification.objects.filter(
        partner=profile,
        is_read=False,
    ).update(is_read=True)

    return response


# ============================================================
#   🆕 GESTIONE CATALOGO PRODOTTI DEL PARTNER
# ============================================================

@login_required
def partner_product_list(request):
    """
    Lista dei prodotti del partner (catalogo personale).
    """
    profile = _get_partner_profile_or_403(request.user)
    if profile is None:
        return HttpResponseForbidden("Non sei abilitato come partner.")

    products = (
        Product.objects
        .filter(supplier=profile)
        .select_related("category")
        .order_by("name")
    )

    context = {
        "partner": profile,
        "products": products,
    }
    return render(request, "partners/product_list.html", context)


@login_required
def partner_product_create(request):
    """
    Creazione di un nuovo prodotto del partner.
    Il supplier viene forzato al PartnerProfile collegato all'utente.
    """
    profile = _get_partner_profile_or_403(request.user)
    if profile is None:
        return HttpResponseForbidden("Non sei abilitato come partner.")

    if request.method == "POST":
        form = PartnerProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.supplier = profile  # forziamo il supplier al partner
            product.save()
            messages.success(request, "Prodotto creato correttamente.")
            return redirect("partners:product_list")
    else:
        form = PartnerProductForm()

    context = {
        "partner": profile,
        "form": form,
        "is_edit": False,
    }
    return render(request, "partners/product_form.html", context)


@login_required
def partner_product_edit(request, product_id):
    """
    Modifica di un prodotto esistente del partner.
    Il partner può modificare solo i propri prodotti.
    """
    profile = _get_partner_profile_or_403(request.user)
    if profile is None:
        return HttpResponseForbidden("Non sei abilitato come partner.")

    product = get_object_or_404(Product, id=product_id, supplier=profile)

    if request.method == "POST":
        form = PartnerProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Prodotto aggiornato correttamente.")
            return redirect("partners:product_list")
    else:
        form = PartnerProductForm(instance=product)

    context = {
        "partner": profile,
        "form": form,
        "product": product,
        "is_edit": True,
    }
    return render(request, "partners/product_form.html", context)


# ============================================================
#   EXPORT RIGHE ORDINE PARTNER (CSV + XLSX)
# ============================================================

@login_required
def partner_order_export_csv(request):
    """
    Esporta in CSV le righe d'ordine del partner,
    applicando gli stessi filtri della lista ordini.
    """
    if getattr(request.user, "role", None) != "partner":
        return HttpResponseForbidden("Area riservata ai partner.")

    partner = get_object_or_404(PartnerProfile, user=request.user)

    # Base queryset
    items = (
        OrderItem.objects
        .filter(partner=partner)
        .select_related("order", "product", "order__structure")
        .order_by("-order__created_at")
    )

    # --- FILTRI (COPIATI DA partner_order_list) ----------------
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Q

    # Stato
    current_status = request.GET.get("status", "").strip()
    if current_status:
        items = items.filter(partner_status=current_status)

    # Periodo
    current_period = request.GET.get("period", "").strip()
    now = timezone.now()

    if current_period == "today":
        items = items.filter(order__created_at__date=now.date())
    elif current_period == "week":
        week_ago = now - timedelta(days=7)
        items = items.filter(order__created_at__date__gte=week_ago.date())
    elif current_period == "month":
        month_ago = now - timedelta(days=30)
        items = items.filter(order__created_at__date__gte=month_ago.date())

    # Ricerca
    current_query = request.GET.get("q", "").strip()
    if current_query:
        items = items.filter(
            Q(order__id__icontains=current_query) |
            Q(product__name__icontains=current_query) |
            Q(order__structure__name__icontains=current_query)
        )

    # --- CREAZIONE CSV -----------------------------------------
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="ordini_partner.csv"'

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "ID Riga",
        "ID Ordine",
        "Struttura",
        "Prodotto",
        "Quantità",
        "Totale",
        "Stato partner",
        "Data ordine",
    ])

    for item in items:
        writer.writerow([
            item.id,
            item.order.id,
            str(item.order.structure),
            item.product.name,
            item.quantity,
            float(item.total_price),
            item.get_partner_status_display(),
            item.order.created_at.strftime("%d/%m/%Y %H:%M"),
        ])

    return response


@login_required
def partner_order_export_xlsx(request):
    """
    Esporta in XLSX le righe d'ordine del partner,
    applicando gli stessi filtri della lista ordini.
    """
    if getattr(request.user, "role", None) != "partner":
        return HttpResponseForbidden("Area riservata ai partner.")

    partner = get_object_or_404(PartnerProfile, user=request.user)

    # Base queryset
    items = (
        OrderItem.objects
        .filter(partner=partner)
        .select_related("order", "product", "order__structure")
        .order_by("-order__created_at")
    )

    # --- FILTRI (COPIATI DA partner_order_list) ----------------
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Q

    # Stato
    current_status = request.GET.get("status", "").strip()
    if current_status:
        items = items.filter(partner_status=current_status)

    # Periodo
    current_period = request.GET.get("period", "").strip()
    now = timezone.now()

    if current_period == "today":
        items = items.filter(order__created_at__date=now.date())
    elif current_period == "week":
        week_ago = now - timedelta(days=7)
        items = items.filter(order__created_at__date__gte=week_ago.date())
    elif current_period == "month":
        month_ago = now - timedelta(days=30)
        items = items.filter(order__created_at__date__gte=month_ago.date())

    # Ricerca
    current_query = request.GET.get("q", "").strip()
    if current_query:
        items = items.filter(
            Q(order__id__icontains=current_query) |
            Q(product__name__icontains=current_query) |
            Q(order__structure__name__icontains=current_query)
        )

    # --- CREAZIONE XLSX ----------------------------------------
    wb = Workbook()
    ws = wb.active
    ws.title = "Ordini Partner"

    headers = [
        "ID Riga",
        "ID Ordine",
        "Struttura",
        "Prodotto",
        "Quantità",
        "Totale",
        "Stato partner",
        "Data ordine",
    ]
    ws.append(headers)

    for item in items:
        ws.append([
            item.id,
            item.order.id,
            str(item.order.structure),
            item.product.name,
            item.quantity,
            float(item.total_price),
            item.get_partner_status_display(),
            item.order.created_at.strftime("%d/%m/%Y %H:%M"),
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="ordini_partner.xlsx"'

    return response
