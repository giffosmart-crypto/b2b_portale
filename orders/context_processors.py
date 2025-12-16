from .cart import Cart


def cart_summary(request):
    """
    Rende disponibili in tutti i template:
        - cart_item_count: numero totale di pezzi nel carrello
        - cart_total: totale carrello

    Solo per utenti autenticati con ruolo 'client' (per sicurezza).
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    # opzionale: se vuoi limitare ai soli client (ed escludere partner)
    if getattr(user, "role", None) == "partner":
        return {}

    cart = Cart(request)
    return {
        "cart_item_count": len(cart),
        "cart_total": cart.get_total_price(),
    }
