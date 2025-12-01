from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from accounts.models import ClientStructure
from catalog.models import Product, Category
from orders.models import Order, OrderItem
from partners.models import PartnerProfile


User = get_user_model()


class AccountsViewsTests(TestCase):
    def setUp(self):
        # Utente client
        self.client_user = User.objects.create_user(
            username="client1",
            email="client@example.com",
            password="pass1234",
            role="client",
            first_name="Cliente",
        )

        # Utente partner
        self.partner_user = User.objects.create_user(
            username="partner1",
            email="partner@example.com",
            password="pass1234",
            role="partner",
            first_name="Partner",
        )

        # Profilo partner
        self.partner_profile = PartnerProfile.objects.create(
            user=self.partner_user,
            company_name="Partner srl",
        )

        # Categoria per i prodotti
        self.category = Category.objects.create(
            name="Categoria test",
            slug="categoria-test",
        )

        # Struttura del client (uso solo campi sicuramente esistenti: owner, name)
        self.structure = ClientStructure.objects.create(
            owner=self.client_user,
            name="Hotel Test",
        )

        # Prodotto
        self.product = Product.objects.create(
            name="Prodotto test",
            description="Descrizione di prova",
            is_service=False,
            supplier=self.partner_profile,
            base_price=Decimal("100.00"),
            unit="pz",
            is_active=True,
            category=self.category,
        )

        # Ordine di prova
        self.order = Order.objects.create(
            client=self.client_user,
            structure=self.structure,
            subtotal=Decimal("100.00"),
            shipping_cost=Decimal("0.00"),
            total=Decimal("100.00"),
            status=Order.STATUS_PENDING_PAYMENT,
        )

        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            partner=self.partner_profile,
            quantity=1,
            unit_price=Decimal("100.00"),
            total_price=Decimal("100.00"),
        )

    # ----------------------
    # LOGIN
    # ----------------------
    def test_login_page_200(self):
        # login è nella app accounts → namespace accounts:login
        url = reverse("accounts:login")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    # ----------------------
    # MY ORDERS
    # ----------------------
    def test_my_orders_requires_login(self):
        url = reverse("accounts:my_orders")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

    def test_my_orders_allowed_for_client(self):
        self.client.login(username="client1", password="pass1234")
        resp = self.client.get(reverse("accounts:my_orders"))
        self.assertEqual(resp.status_code, 200)

    def test_my_orders_forbidden_for_partner(self):
        self.client.login(username="partner1", password="pass1234")
        resp = self.client.get(reverse("accounts:my_orders"))
        self.assertEqual(resp.status_code, 403)

    # ----------------------
    # MY STRUCTURES
    # ----------------------
    def test_my_structures_requires_login(self):
        url = reverse("accounts:my_structures_list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

    def test_my_structures_allowed_for_client(self):
        self.client.login(username="client1", password="pass1234")
        resp = self.client.get(reverse("accounts:my_structures_list"))
        self.assertEqual(resp.status_code, 200)

    def test_my_structures_forbidden_for_partner(self):
        self.client.login(username="partner1", password="pass1234")
        resp = self.client.get(reverse("accounts:my_structures_list"))
        self.assertEqual(resp.status_code, 403)

    # ----------------------
    # MY ORDER DETAIL
    # ----------------------
    def test_my_order_detail_owner_ok(self):
        self.client.login(username="client1", password="pass1234")
        resp = self.client.get(
            reverse("accounts:my_order_detail", args=[self.order.id])
        )
        self.assertEqual(resp.status_code, 200)

    def test_my_order_detail_other_client_404(self):
        other = User.objects.create_user(
            username="other1",
            email="other@example.com",
            password="pass1234",
            role="client",
            first_name="Altro",
        )
        self.client.login(username="other1", password="pass1234")
        resp = self.client.get(
            reverse("accounts:my_order_detail", args=[self.order.id])
        )
        self.assertEqual(resp.status_code, 404)

    def test_my_order_detail_partner_forbidden(self):
        self.client.login(username="partner1", password="pass1234")
        resp = self.client.get(
            reverse("accounts:my_order_detail", args=[self.order.id])
        )
        self.assertEqual(resp.status_code, 403)

    # ----------------------
    # MY ORDER DUPLICATE
    # ----------------------
    def test_my_order_duplicate_requires_login(self):
        url = reverse("accounts:my_order_duplicate", args=[self.order.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

    def test_my_order_duplicate_owner_ok(self):
        self.client.login(username="client1", password="pass1234")
        url = reverse("accounts:my_order_duplicate", args=[self.order.id])
        resp = self.client.get(url)
        # redirect su nuovo ordine
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Order.objects.count(), 2)

def test_my_orders_filters_only_logged_client_orders(self):
        """
        La view 'I miei ordini' deve mostrare solo gli ordini
        del cliente loggato e non quelli di altri clienti.
        """
        # Crea un secondo cliente
        other_client = User.objects.create_user(
            username="other_client",
            email="other_client@example.com",
            password="testpass123",
        )

        # Usa stessi parametri base dell'ordine principale
        other_order = Order.objects.create(
            client=other_client,
            structure=self.structure,  # riuso la struttura creata in setUp
            shipping_cost=self.order.shipping_cost,
            payment_method=self.order.payment_method,
            total=self.order.total,
        )

        # Login come client principale
        self.client.login(username="client", password="testpass123")

        resp = self.client.get(reverse("accounts:my_orders"))
        self.assertEqual(resp.status_code, 200)

        orders = resp.context.get("orders") or resp.context.get("object_list")
        self.assertIsNotNone(orders, "La view my_orders deve passare 'orders' nel contesto")

        # Deve esserci SOLO l'ordine del client loggato
        self.assertIn(self.order, orders)
        self.assertNotIn(other_order, orders)
