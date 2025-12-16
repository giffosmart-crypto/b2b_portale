from datetime import date
from decimal import Decimal

from django.db.models import Sum

from .models import Order, OrderItem, PartnerPayout
from partners.models import PartnerProfile


def build_partner_payouts(period_start: date, period_end: date) -> list[PartnerPayout]:
    """
    Calcola/aggiorna i PartnerPayout per tutti i partner
    nel periodo [period_start, period_end] compreso.

    Logica:
    - considera solo ordini COMPLETED
    - somma le commissioni di OrderItem (commission_amount)
    - per ogni partner fa get_or_create di un PartnerPayout
      con quel periodo, e aggiorna total_commission.
    """
    payouts = []

    # Trova tutte le righe con commissioni in ordini completati nel periodo
    items = (
        OrderItem.objects
        .filter(
            order__status=Order.STATUS_COMPLETED,
            order__created_at__date__gte=period_start,
            order__created_at__date__lte=period_end,
            partner__isnull=False,
        )
        .select_related("partner")
    )

    # Aggrega per partner
    totals_by_partner = (
        items
        .values("partner")
        .annotate(total_commission=Sum("commission_amount"))
    )

    for row in totals_by_partner:
        partner_id = row["partner"]
        total_commission = row["total_commission"] or Decimal("0.00")

        partner = PartnerProfile.objects.get(id=partner_id)

        payout, created = PartnerPayout.objects.get_or_create(
            partner=partner,
            period_start=period_start,
            period_end=period_end,
            defaults={"total_commission": total_commission},
        )

        if not created:
            # Se esiste già, aggiorniamo l'importo (snapshot ricalcolabile)
            payout.total_commission = total_commission
            payout.save(update_fields=["total_commission", "updated_at"])

        payouts.append(payout)

    return payouts
