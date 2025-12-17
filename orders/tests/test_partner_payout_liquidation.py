from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import ClientStructure
from catalog.models import Category, Product
from orders.models import Order, OrderItem, PartnerPayout
from partners.models import PartnerProfile


class PartnerPayoutLiquidationTests(TestCase):
    """Test automatici per la logica payout/liquidazione (patched3).

    Obiettivi:
    - un payout in bozza NON deve liquidare nulla
    - al passaggio a PAID devono liquidarsi SOLO le righe collegate
    - il fallback legacy non deve "rubare" righe già associate ad altri payout
    """

    def setUp(self):
        User = get_user_model()

        # Partner
        self.partner_user = User.objects.create_user(
            username="partner1",
            email="partner1@example.com",
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
            username="client1",
            email="client1@example.com",
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

        # Catalogo minimo
        self.category = Category.objects.create(name="Categoria")
        self.product = Product.objects.create(
            category=self.category,
            name="Prodotto",
            supplier=self.partner,
            base_price=Decimal("100.00"),
            is_active=True,
        )

    def _create_completed_item(self, *, created_at: date, qty: int = 1) -> OrderItem:
        """Crea un ordine con 1 riga completed e commissioni calcolate."""
        order = Order.objects.create(
            client=self.client_user,
            structure=self.structure,
            status=Order.STATUS_COMPLETED,
            subtotal=Decimal("100.00"),
            shipping_cost=Decimal("0.00"),
            total=Decimal("100.00"),
        )
        # forza data ordine nel range desiderato
        Order.objects.filter(pk=order.pk).update(
            created_at=timezone.make_aware(
                timezone.datetime(created_at.year, created_at.month, created_at.day)
            )
        )

        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            partner=self.partner,
            quantity=qty,
            unit_price=Decimal("100.00"),
            total_price=Decimal("100.00") * qty,
            partner_status=OrderItem.PARTNER_STATUS_COMPLETED,
            commission_rate=Decimal("10.00"),
        )
        item.calculate_commission(default_rate=Decimal("10.00"))
        item.save(update_fields=["commission_rate", "commission_amount", "partner_earnings"])
        return item

    def test_draft_payout_does_not_liquidate(self):
        item = self._create_completed_item(created_at=date(2025, 12, 1))

        payout = PartnerPayout.objects.create(
            partner=self.partner,
            period_start=date(2025, 12, 1),
            period_end=date(2025, 12, 31),
            total_commission=item.partner_earnings,
            status=PartnerPayout.STATUS_DRAFT,
        )

        # simuliamo la view backoffice: aggancia la riga al payout ma NON liquida
        item.payout = payout
        item.save(update_fields=["payout"])

        item.refresh_from_db()
        self.assertFalse(item.is_liquidated)
        self.assertEqual(item.payout_id, payout.id)

    def test_paid_payout_liquidates_only_linked_items(self):
        item1 = self._create_completed_item(created_at=date(2025, 12, 2))
        item2 = self._create_completed_item(created_at=date(2025, 12, 3))
        item_other = self._create_completed_item(created_at=date(2025, 12, 4))

        payout = PartnerPayout.objects.create(
            partner=self.partner,
            period_start=date(2025, 12, 1),
            period_end=date(2025, 12, 31),
            total_commission=Decimal("0.00"),
            status=PartnerPayout.STATUS_DRAFT,
        )

        # collega solo item1 e item2
        OrderItem.objects.filter(pk__in=[item1.pk, item2.pk]).update(payout=payout)

        # paga
        payout.status = PartnerPayout.STATUS_PAID
        payout.save()

        item1.refresh_from_db()
        item2.refresh_from_db()
        item_other.refresh_from_db()

        self.assertTrue(item1.is_liquidated)
        self.assertTrue(item2.is_liquidated)
        self.assertFalse(item_other.is_liquidated)
        self.assertIsNone(item_other.payout_id)

    def test_legacy_fallback_does_not_touch_items_already_associated_to_other_payout(self):
        # item già associato ad un payout diverso
        item_linked = self._create_completed_item(created_at=date(2025, 12, 10))
        payout1 = PartnerPayout.objects.create(
            partner=self.partner,
            period_start=date(2025, 12, 1),
            period_end=date(2025, 12, 31),
            total_commission=Decimal("0.00"),
            status=PartnerPayout.STATUS_DRAFT,
        )
        item_linked.payout = payout1
        item_linked.save(update_fields=["payout"])

        # payout2 pagato senza righe collegate: deve usare fallback legacy,
        # ma NON deve "rubare" item_linked (payout__isnull=False)
        payout2 = PartnerPayout.objects.create(
            partner=self.partner,
            period_start=date(2025, 12, 1),
            period_end=date(2025, 12, 31),
            total_commission=Decimal("0.00"),
            status=PartnerPayout.STATUS_DRAFT,
        )
        payout2.status = PartnerPayout.STATUS_PAID
        payout2.save()

        item_linked.refresh_from_db()
        self.assertFalse(item_linked.is_liquidated)
        self.assertEqual(item_linked.payout_id, payout1.id)

    def test_legacy_fallback_liquidates_unassigned_items_in_period(self):
        item_unassigned = self._create_completed_item(created_at=date(2025, 12, 20))
        self.assertIsNone(item_unassigned.payout_id)
        self.assertFalse(item_unassigned.is_liquidated)

        payout = PartnerPayout.objects.create(
            partner=self.partner,
            period_start=date(2025, 12, 1),
            period_end=date(2025, 12, 31),
            total_commission=Decimal("0.00"),
            status=PartnerPayout.STATUS_DRAFT,
        )
        payout.status = PartnerPayout.STATUS_PAID
        payout.save()

        item_unassigned.refresh_from_db()
        self.assertTrue(item_unassigned.is_liquidated)
        self.assertEqual(item_unassigned.payout_id, payout.id)
