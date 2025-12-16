from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth import login, logout
from django.contrib.auth import get_user_model
from django.contrib import messages

from .models import ClientStructure, User
from .forms import (
    ClientStructureForm,
    CustomUserCreationForm,
    ClientProfileForm,
    AdminProfileForm,
)
from orders.models import Order, OrderItem, OrderMessage
from django.urls import reverse
from partners.models import PartnerProfile, PartnerNotification

def _ensure_client(user):
    """
    Ritorna True se l'utente è un cliente, False altrimenti.
    """
    return user.is_authenticated and getattr(user, "role", None) == User.ROLE_CLIENT


# -------- REGISTRAZIONE --------

def register(request):
    """
    Registrazione completa (cliente o partner) usando CustomUserCreationForm.
    Il salvataggio dei campi estesi e del ruolo è già gestito dal form.
    """
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Login automatico dopo la registrazione
            login(request, user)

            messages.success(request, "Registrazione completata con successo.")
            return redirect("home")
    else:
        form = CustomUserCreationForm()

    return render(request, "accounts/register.html", {"form": form})


# ------------ DASHBOARD CLIENTE ------------

@login_required
def my_dashboard(request):
    """
    Dashboard dell'area clienti:
    riepilogo rapido con link a ordini, strutture, profilo.
    Accessibile solo ai clienti.
    """
    user = request.user

    if not _ensure_client(user):
        return HttpResponseForbidden("Area riservata ai clienti.")

    orders_qs = (
        Order.objects
        .filter(client=user)
        .order_by("-created_at")
        .prefetch_related("structure")
    )

    recent_orders = orders_qs[:3]
    total_orders = orders_qs.count()

    context = {
        "user": user,
        "recent_orders": recent_orders,
        "total_orders": total_orders,
    }
    return render(request, "accounts/my_dashboard.html", context)


# ------------ ORDINI CLIENTE ------------

@login_required
def my_orders_list(request):
    # Solo clienti
    if not _ensure_client(request.user):
        return HttpResponseForbidden("Area riservata ai clienti.")

    # Query base ordini del cliente
    orders_qs = (
        Order.objects
        .filter(client=request.user)
        .order_by("-created_at")
        .prefetch_related("items", "structure")
    )

    # Numeri per i 4 box
    total_orders = orders_qs.count()

    # Stati considerati "in corso" (ordine ancora vivo)
    open_statuses = [
        Order.STATUS_PENDING_PAYMENT,
        Order.STATUS_PAID,
        Order.STATUS_PROCESSING,
        Order.STATUS_SHIPPED,
    ]
    open_orders = orders_qs.filter(status__in=open_statuses).count()

    # Completati = realmente conclusi
    completed_orders = orders_qs.filter(status=Order.STATUS_COMPLETED).count()

    # Annullati
    cancelled_orders = orders_qs.filter(status=Order.STATUS_CANCELLED).count()

    # Ultimi 3 ordini (per la sezione "Ultimi ordini")
    recent_orders = orders_qs[:3]

    context = {
        "orders": orders_qs,
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "open_orders": open_orders,
        "cancelled_orders": cancelled_orders,
        "recent_orders": recent_orders,
    }
    return render(request, "accounts/my_orders_list.html", context)

@login_required
def my_order_detail(request, order_id):
    """
    Dettaglio ordine lato cliente:
    - mostra righe ordine
    - mostra cronologia messaggi
    - permette al cliente di inviare un nuovo messaggio
    - invia una notifica al partner quando il cliente scrive
    """
    if not _ensure_client(request.user):
        return HttpResponseForbidden("Area riservata ai clienti.")

    order = get_object_or_404(Order, id=order_id, client=request.user)

    # --- Invio messaggio (POST) ---
    if request.method == "POST":
        text = (request.POST.get("message") or "").strip()

        if text:
            msg = OrderMessage.objects.create(
                order=order,
                sender=request.user,
                sender_role=OrderMessage.ROLE_CLIENT,
                message=text,
            )
            print("DEBUG: Messaggio creato con ID", msg.id)

            # Trova tutti i partner coinvolti nelle righe dell'ordine
            partners = (
                PartnerProfile.objects.filter(order_items__order=order)
                .distinct()
            )

            for partner in partners:
                # prova a costruire un link al dettaglio ordine partner
                try:
                    url = reverse("partners:order_detail", args=[order.id])
                except Exception:
                    # se la route non esiste ancora, lasciamo il link vuoto
                    url = ""

                PartnerNotification.objects.create(
                    partner=partner,
                    title=f"Nuovo messaggio sull'ordine #{order.id}",
                    message=text[:1000],
                    url=url,
                )

            messages.success(request, "Il tuo messaggio è stato inviato al partner.")
        else:
            messages.error(request, "Il messaggio non può essere vuoto.")

        return redirect("accounts:my_order_detail", order_id=order.id)

    # --- GET normale (mostra pagina) ---

    # segna come letti per il CLIENTE tutti i messaggi non ancora letti
    OrderMessage.objects.filter(order=order, is_read_by_client=False).update(
        is_read_by_client=True
    )

    items = order.items.select_related("product", "partner").all()
    order_messages = order.messages.all().order_by("created_at")

    return render(
        request,
        "accounts/my_order_detail.html",
        {
            "order": order,
            "items": items,
            "order_messages": order_messages,
        },
    )
   
    

@login_required
def my_order_duplicate(request, order_id):
    if not _ensure_client(request.user):
        return HttpResponseForbidden("Area riservata ai clienti.")

    order = get_object_or_404(Order, id=order_id, client=request.user)

    # crea una bozza di nuovo ordine con gli stessi dati base
    new_order = Order.objects.create(
        client=order.client,
        structure=order.structure,
        status=Order.STATUS_DRAFT,
        payment_method=order.payment_method,
        subtotal=order.subtotal,
        shipping_cost=order.shipping_cost,
        total=order.total,
        notes=f"Duplicato dall'ordine #{order.id}",
    )

    for item in order.items.all():
        OrderItem.objects.create(
            order=new_order,
            product=item.product,
            partner=item.partner,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
            partner_status=item.partner_status,
        )

    return redirect("accounts:my_order_detail", order_id=new_order.id)


# ------------ STRUTTURE CLIENTE ------------

@login_required
def my_structures_list(request):
    if not _ensure_client(request.user):
        return HttpResponseForbidden("Area riservata ai clienti.")

    structures = ClientStructure.objects.filter(owner=request.user)
    return render(
        request,
        "accounts/my_structures_list.html",
        {"structures": structures},
    )


@login_required
def my_structure_create(request):
    if not _ensure_client(request.user):
        return HttpResponseForbidden("Area riservata ai clienti.")

    if request.method == "POST":
        form = ClientStructureForm(request.POST)
        if form.is_valid():
            structure = form.save(commit=False)
            structure.owner = request.user
            structure.save()
            return redirect("accounts:my_structures_list")
    else:
        form = ClientStructureForm()

    return render(
        request,
        "accounts/structure_form.html",
        {"form": form, "title": "Nuova struttura"},
    )


@login_required
def my_structure_edit(request, pk):
    if not _ensure_client(request.user):
        return HttpResponseForbidden("Area riservata ai clienti.")

    structure = get_object_or_404(ClientStructure, pk=pk, owner=request.user)

    if request.method == "POST":
        form = ClientStructureForm(request.POST, instance=structure)
        if form.is_valid():
            form.save()
            return redirect("accounts:my_structures_list")
    else:
        form = ClientStructureForm(instance=structure)

    return render(
        request,
        "accounts/structure_form.html",
        {"form": form, "title": "Modifica struttura"},
    )


@login_required
def my_structure_delete(request, pk):
    if not _ensure_client(request.user):
        return HttpResponseForbidden("Area riservata ai clienti.")

    structure = get_object_or_404(ClientStructure, pk=pk, owner=request.user)

    if request.method == "POST":
        structure.delete()
        return redirect("accounts:my_structures_list")

    return render(
        request,
        "accounts/structure_confirm_delete.html",
        {"structure": structure},
    )


# ------------ PROFILO UTENTE (DIVISO PER RUOLO) ------------

@login_required
def my_profile(request):
    """
    Pagina profilo lato /my/profile/, con logica diversa per ruolo:

    - CLIENT  -> usa ClientProfileForm (dati anagrafici + aziendali base)
    - ADMIN   -> usa AdminProfileForm (solo dati anagrafici)
    - PARTNER -> redirect all'area partner (/partner/profile/)
    """
    user = request.user
    role_value = getattr(user, "role", None)

    # Se è partner, lo rimandiamo all'area partner
    if role_value == getattr(User, "ROLE_PARTNER", "partner"):
        return redirect("partners:profile")

    # Determina il form in base al ruolo
    if role_value == getattr(User, "ROLE_CLIENT", "client"):
        FormClass = ClientProfileForm
        role_label = "client"
    elif role_value == getattr(User, "ROLE_ADMIN", "admin"):
        FormClass = AdminProfileForm
        role_label = "admin"
    else:
        # Ruolo non riconosciuto: usiamo un form minimale tipo admin
        FormClass = AdminProfileForm
        role_label = "unknown"

    if request.method == "POST":
        form = FormClass(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profilo aggiornato correttamente.")
            return redirect("accounts:my_profile")
    else:
        form = FormClass(instance=user)

    context = {
        "form": form,
        "role": role_label,
    }
    return render(request, "accounts/my_profile.html", context)


@login_required
def profile(request):
    """
    Wrapper di compatibilità:
    reindirizza alla nuova view my_profile.
    """
    return my_profile(request)


@login_required
def logout_view(request):
    """
    Logout semplice via GET: disconnette l'utente e lo rimanda in home.
    """
    logout(request)
    return redirect("/")


# (vecchia versione di my_orders, probabilmente non più usata; puoi rimuoverla in futuro se sei sicuro)
@login_required
def my_orders(request):
    """
    Dashboard cliente storica:
    mantenuta per compatibilità, ma al momento non usata
    se utilizzi my_orders_list e my_dashboard.
    """
    orders_qs = (
        Order.objects
        .filter(client=request.user)
        .select_related("structure")
        .order_by("-created_at")
    )

    total_orders = orders_qs.count()

    open_statuses = [
        Order.STATUS_PENDING_PAYMENT,
        Order.STATUS_PAID,
        Order.STATUS_PROCESSING,
        Order.STATUS_SHIPPED,
    ]

    open_orders = orders_qs.filter(status__in=open_statuses).count()
    completed_orders = orders_qs.filter(status=Order.STATUS_COMPLETED).count()
    cancelled_orders = orders_qs.filter(status=Order.STATUS_CANCELLED).count()

    recent_orders = list(orders_qs[:5])

    context = {
        "orders": orders_qs,
        "total_orders": total_orders,
        "open_orders": open_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "recent_orders": recent_orders,
    }
    return render(request, "accounts/my_orders_list.html", context)
