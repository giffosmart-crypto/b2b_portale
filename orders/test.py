from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from accounts.models import ClientStructure
from catalog.models import Product, Category
from orders.models import Order
from partners.models import PartnerProfile


User = get_user_model()


class OrdersViewsTests(TestCase):
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

        # Struttura cliente (uso solo i campi sicuramente esistenti)
        self.structure = ClientStructure.objects.create(
            owner=self.client_user,
            name="Hotel Test",
        )

        # Prodotto reale
        self.product = Product.objects.create(
            name="Prodotto test",
            description="Descrizione di prova",
            is_service=False,
            supplier=self.partner_profile,
            base_price=Decimal("50.00"),
            unit="pz",
            is_active=True,
            category=self.category,
        )

    def _aggiungi_prodotto_al_carrello(self, user_username):
        """
        Effettua il login con l'utente specificato e usa la view cart_add
        per aggiungere il prodotto al carrello.
        """
        self.client.login(username=user_username, password="pass1234")
        resp = self.client.post(
            reverse("orders:cart_add", args=[self.product.id]),
            {"quantity": 1},
        )
        self.assertEqual(resp.status_code, 302)

    # ----------------------
    # CHECKOUT: permessi
    # ----------------------
    def test_checkout_requires_login(self):
        url = reverse("orders:checkout")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

    def test_checkout_200_for_client_with_items(self):
        self._aggiungi_prodotto_al_carrello("client1")
        resp = self.client.get(reverse("orders:checkout"))
        self.assertEqual(resp.status_code, 200)

    def test_checkout_partner_with_items_still_200(self):
        # Anche se nel mondo reale il partner non dovrebbe fare checkout,
        # per ora la view non fa distinzione di ruolo.
        self._aggiungi_prodotto_al_carrello("partner1")
        resp = self.client.get(reverse("orders:checkout"))
        self.assertEqual(resp.status_code, 200)

    # ----------------------
    # CHECKOUT: creazione ordine
    # ----------------------
    def test_checkout_creates_order_on_post(self):
        # Aggiungo prodotto al carrello come client
        self._aggiungi_prodotto_al_carrello("client1")

        url = reverse("orders:checkout")
        data = {
            "structure": self.structure.id,
            "payment_method": Order.PAYMENT_BANK_TRANSFER,
        }
        resp = self.client.post(url, data)
        
        # redirect su dettaglio ordine
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Order.objects.count(), 1)

        order = Order.objects.first()
        self.assertEqual(order.client, self.client_user)
        self.assertEqual(order.structure, self.structure)
        self.assertEqual(order.items.count(), 1)

        # Il totale deve essere: somma righe + costo spedizione
        items_total = sum(i.total_price for i in order.items.all())
        self.assertEqual(order.total, items_total + order.shipping_cost)

def test_order_status_is_valid_choice(self):
        """
        Lo stato dell'ordine deve essere uno dei valori definiti
        nelle choices del campo 'status'.
        """
        field = Order._meta.get_field("status")
        valid_values = [c[0] for c in field.choices]

        self.assertIn(self.order.status, valid_values)
