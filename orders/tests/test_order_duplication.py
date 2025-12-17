from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import ClientStructure
from catalog.models import Category, Product
from orders.models import Order, OrderItem
from partners.models import PartnerProfile


class OrderDuplicationTests(TestCase):
    """Test automatici per la duplicazione ordine (Runbook 19.6 / 20.4).

    Verifica che la duplicazione:
    - crei un nuovo Order in stato draft
    - ricrei le righe in stato partner_status=pending
    - ricalcoli prezzi/totali usando Product.base_price corrente
    - salti prodotti disattivati
    """

    def setUp(self):
        User = get_user_model()

        # Partner + profilo
        self.partner_user = User.objects.create_user(
            username="partner",
            email="partner@example.com",
            password="pass",
            role=User.ROLE_PARTNER,
        )
        self.partner = PartnerProfile.objects.create(
            user=self.partner_user,
            company_name="Partner Srl",
            vat_number="IT00000000000",
            default_commission_percent=Decimal("10.00"),
        )

        # Cliente + struttura
        self.client_user = User.objects.create_user(
            username="client",
            email="client@example.com",
            password="pass",
            role=User.ROLE_CLIENT,
        )
        self.structure = ClientStructure.objects.create(
            owner=self.client_user,
            name="Struttura 1",
            address="Via Test 1",
            city="Reggio Emilia",
            zip_code="42100",
            country="Italia",
            phone="000000",
            is_default_shipping=True,
        )

        self.category = Category.objects.create(name="Categoria")

        # Prodotto attivo (prezzo attuale diverso da quello usato in ordine originale)
        self.product_active = Product.objects.create(
            category=self.category,
            name="Prodotto Attivo",
            supplier=self.partner,
            base_price=Decimal("60.00"),
            is_active=True,
        )

        # Prodotto disattivo (deve essere saltato in duplicazione)
        self.product_inactive = Product.objects.create(
            category=self.category,
            name="Prodotto Disattivo",
            supplier=self.partner,
            base_price=Decimal("30.00"),
            is_active=False,
        )

    def test_duplicate_order_recalculates_and_skips_inactive(self):
        # ordine originale con prezzi "storici" (diversi da base_price attuale)
        order = Order.objects.create(
            client=self.client_user,
            structure=self.structure,
            status=Order.STATUS_COMPLETED,
            subtotal=Decimal("130.00"),
            shipping_cost=Decimal("0.00"),
            total=Decimal("130.00"),
        )

        # 2x prodotto attivo a 50€ (ma ora base_price è 60€)
        OrderItem.objects.create(
            order=order,
            product=self.product_active,
            partner=self.partner,
            quantity=2,
            unit_price=Decimal("50.00"),
            total_price=Decimal("100.00"),
            partner_status=OrderItem.PARTNER_STATUS_COMPLETED,
        )

        # 1x prodotto disattivo (da saltare)
        OrderItem.objects.create(
            order=order,
            product=self.product_inactive,
            partner=self.partner,
            quantity=1,
            unit_price=Decimal("30.00"),
            total_price=Decimal("30.00"),
            partner_status=OrderItem.PARTNER_STATUS_COMPLETED,
        )

        self.client.force_login(self.client_user)
        url = reverse("accounts:my_order_duplicate", kwargs={"order_id": order.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)

        # nuovo ordine: draft, 1 sola riga (prodotto attivo), prezzo ricalcolato
        new_order = Order.objects.exclude(pk=order.pk).get(client=self.client_user)
        self.assertEqual(new_order.status, Order.STATUS_DRAFT)

        items = list(new_order.items.select_related("product").all())
        self.assertEqual(len(items), 1)
        item = items[0]

        self.assertEqual(item.product_id, self.product_active.id)
        self.assertEqual(item.partner_status, OrderItem.PARTNER_STATUS_PENDING)
        self.assertEqual(item.quantity, 2)

        # unit_price deve essere base_price corrente
        self.assertEqual(item.unit_price, Decimal("60.00"))
        self.assertEqual(item.total_price, Decimal("120.00"))

        # totali ordine ricalcolati
        new_order.refresh_from_db()
        self.assertEqual(new_order.subtotal, Decimal("120.00"))
        self.assertEqual(new_order.shipping_cost, Decimal("0.00"))
        self.assertEqual(new_order.total, Decimal("120.00"))
