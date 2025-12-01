from datetime import timedelta, datetime
from decimal import Decimal
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Product
from partners.models import PartnerProfile
from accounts.models import ClientStructure
from orders.models import Order, OrderItem

User = get_user_model()


class Command(BaseCommand):
    help = "Genera ordini demo per testare il flusso carrello/checkout/partner."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("==> Generazione ordini demo"))

        # 1) Recupero utenti demo (creati da seed_demo_data)
        try:
            client1 = User.objects.get(username="demo_client1")
            client2 = User.objects.get(username="demo_client2")
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                "Utenti demo 'demo_client1' / 'demo_client2' non trovati.\n"
                "Esegui prima: python manage.py seed_demo_data"
            ))
            return

        # 2) Prodotti attivi
        products = list(Product.objects.filter(is_active=True))
        if not products:
            self.stderr.write(self.style.ERROR(
                "Nessun prodotto attivo trovato. Esegui prima: python manage.py seed_demo_data"
            ))
            return

        # 3) Partner (solo se servono per info, non obbligatori)
        _partners = list(PartnerProfile.objects.filter(is_active=True))

        # 4) Assicuriamo di avere una ClientStructure per ciascun client
        field_names = {f.name for f in ClientStructure._meta.fields}

        def ensure_structure_for_client(client, base_name):
            """
            Crea (o recupera) una ClientStructure minimale per il cliente specificato.
            Compila solo i campi che riconosce (name, owner/client/user, address, city, country, ecc.).
            """
            defaults = {}

            # nome struttura se il campo esiste
            if "name" in field_names:
                defaults["name"] = base_name

            # campo utente collegato (owner / client / user)
            for candidate in ["owner", "client", "user"]:
                if candidate in field_names:
                    defaults[candidate] = client
                    break

            # qualche campo testuale comune, se esiste nel modello
            text_fields = ["address", "city", "country", "province", "postal_code"]
            for tf in text_fields:
                if tf in field_names:
                    defaults[tf] = f"Demo {tf}"

            # get_or_create sulla base del name (se esiste), altrimenti su primo campo obbligatorio
            lookup = {}
            if "name" in field_names:
                lookup["name"] = base_name

            structure, created = ClientStructure.objects.get_or_create(
                **lookup,
                defaults=defaults,
            )
            return structure

        structure1 = ensure_structure_for_client(client1, "Struttura demo Riviera")
        structure2 = ensure_structure_for_client(client2, "Struttura demo Colline")

        # 5) Funzione di creazione ordine demo per un cliente
        def create_demo_order(client, structure, index):
            """
            Crea un ordine per il client e la struttura indicati,
            con 1-3 prodotti, subtotal, shipping, total, e righe ordine.
            """
            created_at = datetime.now() - timedelta(days=random.randint(0, 10))

            # selezioniamo 1-3 prodotti a caso
            items = random.sample(products, k=min(len(products), random.randint(1, 3)))

            subtotal = Decimal("0.00")
            shipping_cost = Decimal("10.00")  # fisso per demo

            # creiamo l'ordine usando i CAMPI REALI del tuo modello
            order = Order.objects.create(
                client=client,
                structure=structure,
                status=Order.STATUS_PAID,
                payment_method=Order.PAYMENT_BANK_TRANSFER,
                payment_reference="DEMO",
                subtotal=subtotal,       # lo aggiorniamo dopo
                shipping_cost=shipping_cost,
                total=Decimal("0.00"),   # lo aggiorniamo dopo
                notes=f"Ordine demo generato automaticamente #{index}",
            )

            # creiamo le righe
            for prod in items:
                qty = random.randint(1, 4)
                unit_price = prod.base_price
                line_total = unit_price * qty

                subtotal += line_total

                partner = getattr(prod, "supplier", None)

                OrderItem.objects.create(
                    order=order,
                    product=prod,
                    partner=partner,
                    quantity=qty,
                    unit_price=unit_price,
                    total_price=line_total,
                    partner_status=OrderItem.PARTNER_STATUS_PENDING,
                )

            # aggiorniamo i totali ordine
            order.subtotal = subtotal
            order.total = subtotal + shipping_cost

            # se vuoi forzare la data di creazione (non necessario, ma carino per test)
            if hasattr(order, "created_at"):
                order.created_at = created_at

            order.save()
            return order

        created_orders = []

        # 6) Creiamo qualche ordine per ciascun cliente
        for i in range(1, 4):
            created_orders.append(create_demo_order(client1, structure1, i))
        for i in range(1, 4):
            created_orders.append(create_demo_order(client2, structure2, i))

        self.stdout.write(self.style.SUCCESS(
            f"Creati {len(created_orders)} ordini demo con righe associate."
        ))
        self.stdout.write(self.style.SUCCESS(
            "Puoi vederli in admin (orders.Order / orders.OrderItem) o dalle viste cliente/partner."
        ))
