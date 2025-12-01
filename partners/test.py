from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from accounts.models import ClientStructure
from catalog.models import Product, Category
from orders.models import Order, OrderItem
from partners.models import PartnerProfile


User = get_user_model()


class PartnerViewsTests(TestCase):
    def setUp(self):
        # Client e partner
        self.client_user = User.objects.create_user(
            username="client1",
            email="client@example.com",
            password="pass1234",
            role="client",
            first_name="Cliente",
        )
        self.partner_user = User.objects.create_user(
            username="partner1",
            email="partner@example.com",
            password="pass1234",
            role="partner",
            first_name="Partner",
        )

        self.partner_profile = PartnerProfile.objects.create(
            user=self.partner_user,
            company_name="Partner srl",
        )

        # Categoria
        self.category = Category.objects.create(
            name="Categoria test",
            slug="categoria-test",
        )

        # Struttura cliente - solo campi sicuri
        self.structure = ClientStructure.objects.create(
            owner=self.client_user,
            name="Hotel Test",
        )

        # Prodotto assegnato al partner
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

        # Ordine con item assegnato al partner
        self.order = Order.objects.create(
            client=self.client_user,
            structure=self.structure,
            subtotal=Decimal("100.00"),
            shipping_cost=Decimal("0.00"),
            total=Decimal("100.00"),
            status=Order.STATUS_PENDING_PAYMENT,
        )

        self.item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            partner=self.partner_profile,
            quantity=1,
            unit_price=Decimal("100.00"),
            total_price=Decimal("100.00"),
        )

    # ----------------------
    # DASHBOARD PARTNER
    # ----------------------
    def test_partner_dashboard_requires_login(self):
        url = reverse("partners:dashboard")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        # redirect verso il login (accounts:login)
        self.assertIn(reverse("accounts:login"), resp["Location"])

    def test_partner_dashboard_for_client_redirect(self):
        self.client.login(username="client1", password="pass1234")
        resp = self.client.get(reverse("partners:dashboard"))
        # un client viene rimandato al catalogo
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("catalog:product_list"), resp["Location"])

    def test_partner_dashboard_for_partner_200(self):
        self.client.login(username="partner1", password="pass1234")
        resp = self.client.get(reverse("partners:dashboard"))
        self.assertEqual(resp.status_code, 200)

    # ----------------------
    # LISTA ORDINI PARTNER
    # ----------------------
    def test_partner_order_list_requires_login(self):
        url = reverse("partners:order_list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("accounts:login"), resp["Location"])

    def test_partner_order_list_for_client_redirect(self):
        self.client.login(username="client1", password="pass1234")
        resp = self.client.get(reverse("partners:order_list"))
        # nel tuo codice reale il client riceve 403, non redirect
        self.assertEqual(resp.status_code, 403)

    def test_partner_order_list_for_partner_200(self):
        self.client.login(username="partner1", password="pass1234")
        resp = self.client.get(reverse("partners:order_list"))
        self.assertEqual(resp.status_code, 200)
        # ci aspettiamo che compaia almeno l'ID dell'ordine
        self.assertContains(resp, f"#{self.order.id}")

def test_partner_order_list_filters_items_by_partner(self):
        """
        La lista ordini partner deve mostrare solo le righe d'ordine
        appartenenti al partner loggato, non quelle di altri partner.
        """
        # Crea un secondo partner
        other_partner_user = User.objects.create_user(
            username="other_partner",
            email="other_partner@example.com",
            password="testpass123",
        )
        other_partner = Partner.objects.create(
            user=other_partner_user,
            company_name="Altro Partner Srl",
        )

        # Crea un altro ordine con riga assegnata all'altro partner
        other_order = Order.objects.create(
            client=self.client_user,
            structure=self.structure,
            shipping_cost=self.order.shipping_cost,
            payment_method=self.order.payment_method,
            total=self.order.total,
        )

        other_item = OrderItem.objects.create(
            order=other_order,
            product=self.product,
            partner=other_partner,
            quantity=1,
            unit_price=self.order_item.unit_price,
            total_price=self.order_item.unit_price,
        )

        # Login come partner principale
        self.client.login(username="partner", password="testpass123")
        resp = self.client.get(reverse("partners:partner_order_list"))
        self.assertEqual(resp.status_code, 200)

        items = (
            resp.context.get("items")
            or resp.context.get("order_items")
            or resp.context.get("object_list")
        )
        self.assertIsNotNone(items, "La view partner_order_list deve passare le righe d'ordine nel contesto")

        # Deve contenere la riga del partner loggato
        self.assertIn(self.order_item, items)
        # Non deve contenere la riga di un altro partner
        self.assertNotIn(other_item, items)

def test_partner_can_update_item_status_via_view(self):
        """
        Il partner deve poter aggiornare lo stato di una riga d'ordine
        tramite la view 'update_item_status'.
        """
        # Scelgo un valore di stato diverso da quello attuale partendo dalle choices del modello
        field = OrderItem._meta.get_field("partner_status")
        choices = [c[0] for c in field.choices]

        if len(choices) < 2:
            self.skipTest("Non ci sono abbastanza choices per partner_status per testare l'update")

        current = self.order_item.partner_status
        # prendo un valore diverso da quello attuale
        new_status = choices[0] if current != choices[0] else choices[1]

        self.client.login(username="partner", password="testpass123")
        url = reverse("partners:update_item_status", args=[self.order_item.id])

        resp = self.client.post(url, {"partner_status": new_status}, follow=True)
        # Se la view fa un redirect, con follow=True arrivo a 200
        self.assertEqual(resp.status_code, 200)

        self.order_item.refresh_from_db()
        self.assertEqual(self.order_item.partner_status, new_status)

def test_partner_cannot_update_other_partner_item_status(self):
        """
        Un partner non deve poter aggiornare lo stato di una riga d'ordine
        appartenente ad un altro partner.
        """
        other_partner_user = User.objects.create_user(
            username="other_partner2",
            email="other_partner2@example.com",
            password="testpass123",
        )
        other_partner = Partner.objects.create(
            user=other_partner_user,
            company_name="Altro Partner 2 Srl",
        )

        other_order = Order.objects.create(
            client=self.client_user,
            structure=self.structure,
            shipping_cost=self.order.shipping_cost,
            payment_method=self.order.payment_method,
            total=self.order.total,
        )

        other_item = OrderItem.objects.create(
            order=other_order,
            product=self.product,
            partner=other_partner,
            quantity=1,
            unit_price=self.order_item.unit_price,
            total_price=self.order_item.unit_price,
        )

        self.client.login(username="partner", password="testpass123")
        url = reverse("partners:update_item_status", args=[other_item.id])

        resp = self.client.post(url, {"partner_status": other_item.partner_status})
        # se la view usa get_object_or_404 con filtro sul partner → 404
        self.assertIn(resp.status_code, (403, 404))


