from decimal import Decimal


def calculate_shipping(cart, structure):
    """
    Calcola le spese di spedizione in base al contenuto del carrello
    e alla struttura di consegna.

    Esempio semplice:
      - Ordini con totale < 200 €  -> 9.90 €
      - Ordini con totale >= 200 € -> spedizione gratuita
    """
    total = cart.get_total_price()

    # se il carrello è vuoto, niente spedizione
    if total <= 0:
        return Decimal("0.00")

    if total >= Decimal("200.00"):
        return Decimal("0.00")

    return Decimal("9.90")
