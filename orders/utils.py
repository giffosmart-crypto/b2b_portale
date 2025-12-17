from decimal import Decimal

from catalog.models import Product
from partners.models import PartnerProfile, PartnerCategoryCommission


def get_commission_rate_for_item(partner: PartnerProfile, product: Product) -> Decimal:
    """
    Restituisce la commissione da applicare per una riga ordine
    seguendo la priorità:

    1) product.partner_commission_rate (se valorizzato)
    2) PartnerCategoryCommission(partner, product.category)
    3) partner.default_commission_percent
    """

    # 1) Commissione specifica prodotto
    product_rate = getattr(product, "partner_commission_rate", None)
    if product_rate is not None:
        return product_rate

    # 2) Commissione categoria per questo partner
    if product.category_id:
        try:
            cat_commission = PartnerCategoryCommission.objects.get(
                partner=partner,
                category=product.category,
            )
            return cat_commission.commission_rate
        except PartnerCategoryCommission.DoesNotExist:
            pass

    # 3) Fallback: default partner (campo reale su PartnerProfile)
    default_rate = getattr(partner, "default_commission_percent", None)
    if default_rate is not None:
        return default_rate

    # fallback finale di sicurezza
    return Decimal("0.00")
