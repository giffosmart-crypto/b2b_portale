from decimal import Decimal

from django.db.models import Sum, DecimalField, Value
from django.db.models.functions import Coalesce
from django.template.loader import render_to_string

from weasyprint import HTML

from .models import PartnerPayout  # adatta se il path è diverso


def render_payout_pdf_bytes(payout: PartnerPayout) -> bytes:
    """
    Genera un PDF (bytes) per il payout usando il template
    backoffice/partner_payout_report.html
    """

    # Righe collegate a questo payout
    items_qs = (
        payout.items
        .select_related("order", "order__client", "product")
        .order_by("order__created_at", "id")
    )

    aggregates = items_qs.aggregate(
        total_row_amount=Coalesce(
            Sum("total_price"),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
        total_commission=Coalesce(
            Sum("commission_amount"),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
        total_partner_net=Coalesce(
            Sum("partner_earnings"),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
    )

    context = {
        "payout": payout,
        "items": items_qs,
        "total_row_amount": aggregates["total_row_amount"],
        "total_commission": aggregates["total_commission"],
        "total_partner_net": aggregates["total_partner_net"],
    }

    html = render_to_string("backoffice/partner_payout_report.html", context)
    pdf_bytes = HTML(string=html).write_pdf()
    return pdf_bytes
