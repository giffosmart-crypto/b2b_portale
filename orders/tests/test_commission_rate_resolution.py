from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from catalog.models import Category, Product
from partners.models import PartnerProfile, PartnerCategoryCommission
from orders.utils import get_commission_rate_for_item
from uuid import uuid4
from django.utils.text import slugify

class CommissionRateResolutionTests(TestCase):
    """Test automatici per la priorità commissionale:

    1) commissione specifica prodotto
    2) commissione categoria per partner
    3) commissione default partner
    """

    def setUp(self):
        User = get_user_model()

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

        self.cat_x = Category.objects.create(
            name="Categoria X",
            slug=f"{slugify('Categoria X')}-{uuid4().hex[:8]}",
        )

        self.cat_y = Category.objects.create(
            name="Categoria Y",
            slug=f"{slugify('Categoria Y')}-{uuid4().hex[:8]}",
        )

        # Commissione categoria (partner, cat_x)
        PartnerCategoryCommission.objects.create(
            partner=self.partner,
            category=self.cat_x,
            commission_rate=Decimal("15.00"),
        )

        # Prodotto A: commissione specifica prodotto
        self.prod_a = Product.objects.create(
            category=self.cat_x,
            name="Prodotto A",
            supplier=self.partner,
            base_price=Decimal("100.00"),
            partner_commission_rate=Decimal("20.00"),
            is_active=True,
        )

        # Prodotto B: solo commissione categoria
        self.prod_b = Product.objects.create(
            category=self.cat_x,
            name="Prodotto B",
            supplier=self.partner,
            base_price=Decimal("100.00"),
            partner_commission_rate=None,
            is_active=True,
        )

        # Prodotto C: nessuna commissione categoria -> fallback default partner
        self.prod_c = Product.objects.create(
            category=self.cat_y,
            name="Prodotto C",
            supplier=self.partner,
            base_price=Decimal("100.00"),
            partner_commission_rate=None,
            is_active=True,
        )

    def test_rate_product_overrides_category_and_partner(self):
        rate = get_commission_rate_for_item(self.partner, self.prod_a)
        self.assertEqual(rate, Decimal("20.00"))

    def test_rate_category_overrides_partner_default(self):
        rate = get_commission_rate_for_item(self.partner, self.prod_b)
        self.assertEqual(rate, Decimal("15.00"))

    def test_rate_partner_default_is_fallback(self):
        rate = get_commission_rate_for_item(self.partner, self.prod_c)
        self.assertEqual(rate, Decimal("10.00"))
