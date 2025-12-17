from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import ClientStructure
from catalog.models import Category, Product, ProductRating
from orders.models import Order, OrderItem
from partners.models import PartnerProfile


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="noreply@example.com",
)
class ReviewInvitesCommandTests(TestCase):
    """Test automatici per invito + reminder recensioni (Runbook 26).

    Verifica:
    - invito inviato solo per ordini completed nel range e non già invitati
    - reminder inviato una sola volta dopo N giorni dall'invito
    - nessun invio se tutti i prodotti sono già recensiti
    """

    def setUp(self):
        User = get_user_model()

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
        self.product = Product.objects.create(
            category=self.category,
            name="Prodotto",
            supplier=self.partner,
            base_price=Decimal("100.00"),
            is_active=True,
        )

    def _create_completed_order(self, *, created_at: timezone.datetime) -> Order:
        order = Order.objects.create(
            client=self.client_user,
            structure=self.structure,
            status=Order.STATUS_COMPLETED,
            subtotal=Decimal("100.00"),
            shipping_cost=Decimal("0.00"),
            total=Decimal("100.00"),
        )
        Order.objects.filter(pk=order.pk).update(created_at=created_at)
        OrderItem.objects.create(
            order=order,
            product=self.product,
            partner=self.partner,
            quantity=1,
            unit_price=Decimal("100.00"),
            total_price=Decimal("100.00"),
            partner_status=OrderItem.PARTNER_STATUS_COMPLETED,
            commission_rate=Decimal("10.00"),
        )
        return order

    def test_invite_sent_for_completed_order_and_marks_timestamp(self):
        now = timezone.now()
        order = self._create_completed_order(created_at=now - timedelta(days=3))

        mail.outbox.clear()
        call_command("send_review_invites")

        order.refresh_from_db()
        self.assertIsNotNone(order.review_invite_sent_at)
        self.assertIsNone(order.review_reminder_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(order.client.email, mail.outbox[0].to)

    def test_reminder_sent_after_invite_and_only_once(self):
        now = timezone.now()
        order = self._create_completed_order(created_at=now - timedelta(days=20))

        # Simula invito già inviato 9 giorni fa, reminder non inviato
        Order.objects.filter(pk=order.pk).update(
            review_invite_sent_at=now - timedelta(days=9),
            review_reminder_sent_at=None,
        )

        mail.outbox.clear()
        call_command("send_review_invites")

        order.refresh_from_db()
        self.assertIsNotNone(order.review_reminder_sent_at)
        self.assertEqual(len(mail.outbox), 1)

        # Secondo run: non deve inviare altri reminder
        mail.outbox.clear()
        call_command("send_review_invites")
        self.assertEqual(len(mail.outbox), 0)

    def test_no_invite_if_all_products_already_rated(self):
        now = timezone.now()
        order = self._create_completed_order(created_at=now - timedelta(days=3))

        # L'utente ha già recensito il prodotto
        ProductRating.objects.create(
            product=self.product,
            user=self.client_user,
            rating=5,
            comment="ok",
            is_approved=True,
        )

        mail.outbox.clear()
        call_command("send_review_invites")

        order.refresh_from_db()
        self.assertIsNone(order.review_invite_sent_at)
        self.assertEqual(len(mail.outbox), 0)
