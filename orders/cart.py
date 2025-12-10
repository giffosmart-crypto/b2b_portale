from decimal import Decimal

from django.conf import settings  # eventualmente usabile in futuro
from catalog.models import Product

CART_SESSION_ID = "cart"


class Cart:
    """
    Carrello basato su sessione.

    Struttura interna:
        session[CART_SESSION_ID] = {
            "<product_id>": {
                "quantity": <int>,
                "price": "<str Decimal>",
            },
            ...
        }
    """

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_ID)
        if not cart:
            cart = self.session[CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, override_quantity=False):
        """
        Aggiunge un prodotto al carrello o aggiorna la quantità.

        - quantity: intero positivo
        - override_quantity=True → imposta la quantità esatta
        - override_quantity=False → somma alla quantità esistente
        """
        product_id = str(product.id)
        quantity = int(quantity)

        if product_id not in self.cart:
            self.cart[product_id] = {
                "quantity": 0,
                "price": str(product.base_price),
            }

        if override_quantity:
            self.cart[product_id]["quantity"] = max(quantity, 0)
        else:
            self.cart[product_id]["quantity"] += max(quantity, 0)

        self.save()

    def remove(self, product):
        """
        Rimuove completamente un prodotto dal carrello.
        """
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def save(self):
        """
        Segna la sessione come modificata.
        """
        self.session.modified = True

    def __iter__(self):
        """
        Itera sugli elementi del carrello e aggiunge gli oggetti Product reali,
        i prezzi come Decimal e il totale riga.
        """
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        cart = self.cart.copy()

        for product in products:
            item = cart[str(product.id)]
            item["product"] = product
            item["price"] = Decimal(item["price"])
            item["quantity"] = int(item["quantity"])
            item["total_price"] = item["price"] * item["quantity"]
            yield item

    def __len__(self):
        """
        Numero totale di pezzi nel carrello (somma delle quantità).
        """
        return sum(int(item["quantity"]) for item in self.cart.values())

    def get_total_price(self):
        """
        Totale complessivo del carrello.
        """
        return sum(
            Decimal(item["price"]) * int(item["quantity"])
            for item in self.cart.values()
        )

    def clear(self):
        """
        Svuota completamente il carrello.
        """
        if CART_SESSION_ID in self.session:
            del self.session[CART_SESSION_ID]
            self.save()

    def is_empty(self):
        """
        True se il carrello è vuoto, False altrimenti.
        """
        return len(self) == 0
