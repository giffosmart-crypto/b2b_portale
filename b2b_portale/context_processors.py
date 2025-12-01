from orders.models import OrderItem

def partner_notifications(request):
    """
    Aggiunge al contesto globale il numero di righe d'ordine aperte
    per il partner loggato (se l'utente è un partner).
    """
    user = request.user
    if not user.is_authenticated or getattr(user, "role", None) != "partner":
        return {}

    # Import locale per evitare import circolari
    try:
        partner = user.partnerprofile
    except Exception:
        return {}

    open_statuses = [
        OrderItem.PARTNER_STATUS_PENDING,
        OrderItem.PARTNER_STATUS_ACCEPTED,
        OrderItem.PARTNER_STATUS_IN_PROGRESS,
        OrderItem.PARTNER_STATUS_SHIPPED,
    ]

    open_count = (
        OrderItem.objects
        .filter(partner=partner, partner_status__in=open_statuses)
        .count()
    )

    return {
        "partner_open_items_count": open_count,
    }
