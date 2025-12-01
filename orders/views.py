from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

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
    return redirect("orders:cart_detail")


@login_required
def cart_remove(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = Cart(request)
    cart.remove(product)
    messages.info(request, f"{product.name} è stato rimosso dal carrello.")
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
                        update_fields=["commission_rate", "commission_amount"]
                    )

            # Svuota il carrello e mostra conferma
            cart.clear()
            return render(
                request,
                "orders/order_confirmation.html",
                {"order": order},
            )
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
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, client=request.user)
    return render(request, "orders/order_detail.html", {"order": order})
