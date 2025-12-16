# partners/context_processors.py
from .models import PartnerProfile
from orders.models import OrderItem

from django.contrib.auth import get_user_model
from .models import PartnerNotification

User = get_user_model()


def partner_sidebar_counters(request):
    """
    Aggiunge al contesto:
    - partner_open_items_count
    - partner_unread_notifications_count
    visibili in tutti i template (es. base.html).
    """
    user = request.user

    if not user.is_authenticated or getattr(user, "role", None) != "partner":
        return {}

    # Se non ha ancora un profilo partner, non facciamo nulla
    partner_profile = getattr(user, "partner_profile", None)
    if partner_profile is None:
        return {}

    # Ordini da evadere (stessi stati che usiamo nella lista ordini)
    open_statuses = [
        OrderItem.PARTNER_STATUS_PENDING,
        OrderItem.PARTNER_STATUS_ACCEPTED,
        OrderItem.PARTNER_STATUS_IN_PROGRESS,
        OrderItem.PARTNER_STATUS_SHIPPED,
    ]

    open_items_count = (
        OrderItem.objects
        .filter(partner=partner_profile, partner_status__in=open_statuses)
        .count()
    )

    # Notifiche non lette
    unread_notifications_count = (
        PartnerNotification.objects
        .filter(partner=partner_profile, is_read=False)
        .count()
    )

    return {
        "partner_open_items_count": open_items_count,
        "partner_unread_notifications_count": unread_notifications_count,
    }


def partner_dashboard_counts(request):
    """
    Rende disponibili nelle template alcuni numeri
    sugli ordini del partner loggato.
    """
    user = request.user
    if not user.is_authenticated:
        return {}

    # Deve essere un partner
    if getattr(user, "role", None) != "partner":
        return {}

    try:
        # ATTENZIONE: il related_name corretto è partner_profile
        partner_profile = user.partner_profile
    except PartnerProfile.DoesNotExist:
        return {}

    qs = OrderItem.objects.filter(partner=partner_profile)

    open_statuses = [
        OrderItem.PARTNER_STATUS_PENDING,
        OrderItem.PARTNER_STATUS_ACCEPTED,
        OrderItem.PARTNER_STATUS_IN_PROGRESS,
        OrderItem.PARTNER_STATUS_SHIPPED,
    ]

    total_items = qs.count()
    open_items = qs.filter(partner_status__in=open_statuses).count()
    completed_items = qs.filter(
        partner_status=OrderItem.PARTNER_STATUS_COMPLETED
    ).count()
    rejected_items = qs.filter(
        partner_status=OrderItem.PARTNER_STATUS_REJECTED
    ).count()

    # Questo lo usi nel menu per il bollino
    partner_open_items_count = open_items

    return {
        "partner_total_items": total_items,
        "partner_open_items": open_items,
        "partner_completed_items": completed_items,
        "partner_rejected_items": rejected_items,
        "partner_open_items_count": partner_open_items_count,
    }
