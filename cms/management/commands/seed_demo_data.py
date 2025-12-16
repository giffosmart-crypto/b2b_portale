from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction


from catalog.models import Category, Product, ProductAvailability
from partners.models import PartnerProfile

User = get_user_model()

# Se questi import non esistono nel tuo progetto, la parte ordini verrà saltata
try:
    from orders.models import Order, OrderItem
    HAVE_ORDERS = True
except Exception:
    Order = None
    OrderItem = None
    HAVE_ORDERS = False

try:
    from accounts.models import Structure
    HAVE_STRUCTURE = True
except Exception:
    Structure = None
    HAVE_STRUCTURE = False


class Command(BaseCommand):
    help = "Popola il database con dati demo per testare il portale B2B."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("==> Creazione utenti demo"))

        # Utenti demo (password uguale per tutti)
        demo_password = "Demo12345!"

        demo_client1, _ = User.objects.get_or_create(
            username="demo_client1",
            defaults={"email": "client1@example.com"},
        )
        demo_client1.set_password(demo_password)
        demo_client1.save()

        demo_client2, _ = User.objects.get_or_create(
            username="demo_client2",
            defaults={"email": "client2@example.com"},
        )
        demo_client2.set_password(demo_password)
        demo_client2.save()

        partner_user1, _ = User.objects.get_or_create(
            username="demo_partner1",
            defaults={"email": "partner1@example.com"},
        )
        partner_user1.set_password(demo_password)
        partner_user1.save()

        partner_user2, _ = User.objects.get_or_create(
            username="demo_partner2",
            defaults={"email": "partner2@example.com"},
        )
        partner_user2.set_password(demo_password)
        partner_user2.save()

        self.stdout.write(self.style.SUCCESS("   - Utenti demo creati/aggiornati"))

        # Profili partner
        self.stdout.write(self.style.MIGRATE_HEADING("==> Creazione profili partner"))

        partner1, _ = PartnerProfile.objects.get_or_create(
            user=partner_user1,
            defaults={
                "company_name": "Tour Operator Riviera",
                "is_active": True,
            },
        )
        partner2, _ = PartnerProfile.objects.get_or_create(
            user=partner_user2,
            defaults={
                "company_name": "Hotel & Spa Dolomiti",
                "is_active": True,
            },
        )

        self.stdout.write(self.style.SUCCESS("   - PartnerProfile creati/aggiornati"))

        # Categorie
        self.stdout.write(self.style.MIGRATE_HEADING("==> Creazione categorie"))

        cat_hotel, _ = Category.objects.get_or_create(
            slug="hotel",
            defaults={"name": "Hotel", "is_active": True},
        )
        cat_tour, _ = Category.objects.get_or_create(
            slug="escursioni",
            defaults={"name": "Escursioni", "is_active": True},
        )
        cat_transfer, _ = Category.objects.get_or_create(
            slug="transfer",
            defaults={"name": "Transfer", "is_active": True},
        )
        cat_pacchetti, _ = Category.objects.get_or_create(
            slug="pacchetti",
            defaults={"name": "Pacchetti vacanza", "is_active": True},
        )

        self.stdout.write(self.style.SUCCESS("   - Categorie create/aggiornate"))

        # Prodotti / servizi
        self.stdout.write(self.style.MIGRATE_HEADING("==> Creazione prodotti/servizi demo"))

        products_data = [
            # Partner 1 - tour operator
            {
                "name": "Escursione in barca alle isole",
                "slug": "escursione-barca-isole",
                "category": cat_tour,
                "supplier": partner1,
                "is_service": True,
                "base_price": Decimal("69.00"),
                "unit": "per_persona",  # adatta al tuo UNIT_CHOICES
                "short_description": "Mezza giornata in barca con guida e aperitivo a bordo.",
                "description": "Partenza ore 9:00 dal porto principale, rientro ore 13:30. Include skipper, carburante, bevande e aperitivo.",
            },
            {
                "name": "Tour enogastronomico colline",
                "slug": "tour-enogastronomico-colline",
                "category": cat_tour,
                "supplier": partner1,
                "is_service": True,
                "base_price": Decimal("89.00"),
                "unit": "per_persona",
                "short_description": "Tour guidato con degustazioni in 3 cantine locali.",
                "description": "Durata intera giornata. Transfer incluso dalla struttura del cliente.",
            },
            {
                "name": "Transfer privato aeroporto → hotel",
                "slug": "transfer-privato-aeroporto-hotel",
                "category": cat_transfer,
                "supplier": partner1,
                "is_service": True,
                "base_price": Decimal("49.00"),
                "unit": "per_veicolo",
                "short_description": "Transfer privato fino a 3 persone, bagagli inclusi.",
                "description": "Accoglienza in aeroporto con cartello nominativo, viaggio in auto/minivan climatizzato.",
            },
            # Partner 2 - hotel & spa
            {
                "name": "Camera doppia standard BB",
                "slug": "camera-doppia-standard-bb",
                "category": cat_hotel,
                "supplier": partner2,
                "is_service": True,
                "base_price": Decimal("120.00"),
                "unit": "per_notte",
                "short_description": "Camera doppia con colazione inclusa.",
                "description": "Camera 18mq, letto matrimoniale, colazione a buffet, Wi-Fi, SPA a pagamento.",
            },
            {
                "name": "Pacchetto weekend benessere",
                "slug": "pacchetto-weekend-benessere",
                "category": cat_pacchetti,
                "supplier": partner2,
                "is_service": True,
                "base_price": Decimal("320.00"),
                "unit": "per_soggiorno",
                "short_description": "2 notti, SPA illimitata, massaggio inclusi.",
                "description": "Arrivo venerdì, partenza domenica. Include trattamento SPA, un massaggio a persona, cena degustazione.",
            },
        ]

        created_products = []

        for pdata in products_data:
            product, _ = Product.objects.get_or_create(
                slug=pdata["slug"],
                defaults={
                    "name": pdata["name"],
                    "category": pdata["category"],
                    "supplier": pdata["supplier"],
                    "is_service": pdata["is_service"],
                    "base_price": pdata["base_price"],
                    "unit": pdata["unit"],
                    "short_description": pdata["short_description"],
                    "description": pdata["description"],
                    "is_active": True,
                },
            )
            created_products.append(product)

        self.stdout.write(self.style.SUCCESS(f"   - Creati/aggiornati {len(created_products)} prodotti"))

        # Disponibilità base per i prossimi 14 giorni
        self.stdout.write(self.style.MIGRATE_HEADING("==> Creazione disponibilità demo"))

        today = date.today()
        for product in created_products:
            for offset in range(0, 14):
                d = today + timedelta(days=offset)
                ProductAvailability.objects.get_or_create(
                    product=product,
                    date=d,
                    defaults={"available_quantity": 10},
                )

        self.stdout.write(self.style.SUCCESS("   - Disponibilità create per i prossimi 14 giorni"))

        # Strutture e ordini demo (se i modelli esistono)
        if HAVE_STRUCTURE and HAVE_ORDERS:
            self.stdout.write(self.style.MIGRATE_HEADING("==> Creazione strutture e ordini demo"))

            struct1, _ = Structure.objects.get_or_create(
                name="Hotel Test Riviera",
                defaults={
                    "owner": demo_client1,
                    "address": "Via Litoranea 10",
                    "city": "Rimini",
                    "country": "Italia",
                },
            )
            struct2, _ = Structure.objects.get_or_create(
                name="B&B Colline Verdi",
                defaults={
                    "owner": demo_client2,
                    "address": "Via delle Colline 5",
                    "city": "Reggio Emilia",
                    "country": "Italia",
                },
            )

            # Primo ordine per client1
            try:
                order1 = Order.objects.create(
                    customer=demo_client1,
                    structure=struct1,
                    # adatta questi campi ai nomi reali del tuo modello Order:
                    status="confirmed",
                    total_amount=Decimal("0.00"),
                )
                total = Decimal("0.00")
                for product in created_products[:2]:
                    item = OrderItem.objects.create(
                        order=order1,
                        product=product,
                        quantity=2,
                        unit_price=product.base_price,
                        partner=product.supplier,
                        partner_status="pending",
                    )
                    total += item.unit_price * item.quantity
                order1.total_amount = total
                order1.save()
            except Exception as e:
                self.stderr.write(
                    self.style.WARNING(f"   ! Impossibile creare ordine demo 1: {e}")
                )

            # Secondo ordine per client2
            try:
                order2 = Order.objects.create(
                    customer=demo_client2,
                    structure=struct2,
                    status="pending",
                    total_amount=Decimal("0.00"),
                )
                total = Decimal("0.00")
                for product in created_products[2:]:
                    item = OrderItem.objects.create(
                        order=order2,
                        product=product,
                        quantity=1,
                        unit_price=product.base_price,
                        partner=product.supplier,
                        partner_status="pending",
                    )
                    total += item.unit_price * item.quantity
                order2.total_amount = total
                order2.save()
            except Exception as e:
                self.stderr.write(
                    self.style.WARNING(f"   ! Impossibile creare ordine demo 2: {e}")
                )

            self.stdout.write(self.style.SUCCESS("   - Strutture e ordini demo creati (se possibile)"))
        else:
            self.stdout.write(
                self.style.WARNING(
                    "   ! Modelli Structure/Order/OrderItem non trovati: salto creazione ordini demo."
                )
            )

        self.stdout.write(self.style.SUCCESS("\n==> Dati demo creati con successo."))
        self.stdout.write(self.style.SUCCESS("   Utenti di test (password uguale per tutti):"))
        self.stdout.write("      - demo_client1 / Demo12345!")
        self.stdout.write("      - demo_client2 / Demo12345!")
        self.stdout.write("      - demo_partner1 / Demo12345!")
        self.stdout.write("      - demo_partner2 / Demo12345!")
