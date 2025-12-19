from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings
from django.views.decorators.http import require_POST

from catalog.models import Product
from partners.models import PartnerProfile
from .cart import Cart
from .forms import CheckoutForm
from .models import Order, OrderItem, OrderMessage
from .shipping import calculate_shipping


@login_required
def cart_detail(request):
    cart = Cart(request)
    return render(request, "orders/cart_detail.html", {"cart": cart})


@login_required
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart = Cart(request)

    # per semplicità: aggiunge sempre +1
    cart.add(product=product, quantity=1)
    messages.success(request, f"{product.name} è stato aggiunto al carrello.")

    # Se presente, torniamo alla pagina precedente (es. catalogo) invece di forzare la pagina carrello.
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)

    return redirect("orders:cart_detail")


@require_POST
@login_required
def cart_update(request, product_id):
    """
    Aggiorna la quantità di un prodotto nel carrello.
    Se quantity <= 0 rimuove il prodotto.
    """
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart = Cart(request)

    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        quantity = 1

    if quantity <= 0:
        cart.remove(product)
        messages.info(request, f"{product.name} è stato rimosso dal carrello.")
    else:
        cart.add(product=product, quantity=quantity, override_quantity=True)
        messages.success(
            request,
            f"La quantità di {product.name} è stata aggiornata a {quantity}.",
        )

    return redirect("orders:cart_detail")


@login_required
def cart_remove(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = Cart(request)
    cart.remove(product)
    messages.info(request, f"{product.name} è stato rimosso dal carrello.")
    return redirect("orders:cart_detail")


@require_POST
@login_required
def cart_clear(request):
    """
    Svuota completamente il carrello.
    """
    cart = Cart(request)
    cart.clear()
    messages.info(request, "Il carrello è stato svuotato.")
    return redirect("orders:cart_detail")


@login_required
def checkout(request):
    cart = Cart(request)

    # Carrello vuoto -> pagina dedicata
    if cart.is_empty():
        return render(request, "orders/empty_cart.html")

    if request.method == "POST":
        # dati del form + utente passato come parametro extra
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            structure = form.cleaned_data["structure"]
            payment_method = form.cleaned_data["payment_method"]
            notes = form.cleaned_data.get("notes", "")

            subtotal = cart.get_total_price()
            shipping_cost = calculate_shipping(cart, structure)
            total = subtotal + shipping_cost

            # CREA ORDINE
            order = Order.objects.create(
                client=request.user,
                structure=structure,
                subtotal=subtotal,
                shipping_cost=shipping_cost,
                payment_method=payment_method,
                total=total,
                notes=notes,
            )

            # CREA RIGHE D’ORDINE
            for item in cart:
                product = item["product"]
                quantity = item["quantity"]
                unit_price = item["price"]
                total_price = item["total_price"]

                partner = getattr(product, "supplier", None)

                order_item = OrderItem.objects.create(
                    order=order,
                    product=product,
                    partner=partner,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=total_price,
                )

                # 🔹 Calcolo commissione di default subito (se c'è un partner)
                if partner:
                    default_rate = partner.default_commission_percent or Decimal("0.00")
                    order_item.commission_rate = default_rate
                    order_item.calculate_commission(default_rate=default_rate)
                    order_item.save(
                        update_fields=["commission_rate", "commission_amount", "partner_earnings"]
                    )

            # Svuota il carrello e mostra conferma
            cart.clear()
            return redirect("orders:order_confirmation", order_id=order.id)
    else:
        # form non bound, ma con l'utente passato correttamente
        form = CheckoutForm(user=request.user)

    return render(
        request,
        "orders/checkout.html",
        {
            "cart": cart,
            "form": form,
        },
    )


@login_required
def order_confirmation(request, order_id: int):
    order = get_object_or_404(Order, id=order_id, client=request.user)
    return render(request, "orders/order_confirmation.html", {"order": order})


@login_required
def order_detail(request, order_id):
    """
    Dettaglio ordine lato cliente.

    - mostra le righe ordine (items)
    - mostra i messaggi legati all'ordine (order_messages)
    - gestisce l'invio di un nuovo messaggio tramite POST
    """
    order = get_object_or_404(Order, id=order_id, client=request.user)

    # Se arriva un POST, gestiamo l'invio del messaggio
    if request.method == "POST":
        text = (request.POST.get("message") or "").strip()

        if text:
            OrderMessage.objects.create(
                order=order,
                sender=request.user,
                sender_role=OrderMessage.ROLE_CLIENT,
                message=text,
            )
            messages.success(
                request,
                "Il tuo messaggio è stato inviato al partner.",
            )
        else:
            messages.error(
                request,
                "Il messaggio non può essere vuoto.",
            )

        # redirect per evitare il re-invio del form con refresh
        return redirect("orders:order_detail", order_id=order.id)

    # Dati per il template (GET normale)
    items = order.items.select_related("product", "partner").all()
    order_messages = order.messages.all()

    return render(
        request,
        "orders/order_detail.html",
        {
            "order": order,
            "items": items,
            "order_messages": order_messages,
        },
    )
