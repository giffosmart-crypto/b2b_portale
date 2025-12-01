# orders/test_cart.py

from django.test import TestCase

from catalog.models import Category, Product
from .cart import Cart


class DummySession(dict):
    """
    Mock semplice di una sessione Django:
    - si comporta come un dict
    - espone l'attributo 'modified' usato da Cart.save()
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.modified = False


class DummyRequest:
    """
    Finto oggetto request con una sola cosa che ci interessa:
    - request.session
    """
    def __init__(self):
        self.session = DummySession()


class CartTests(TestCase):
    def setUp(self):
        # Request finto -> session finta
        self.request = DummyRequest()
        self.cart = Cart(self.request)

        # Categoria e prodotti di test
        self.category = Category.objects.create(
            name="Categoria Test",
            slug="categoria-test",
        )

        self.product1 = Product.objects.create(
            name="Prodotto A",
            slug="prodotto-a",
            category=self.category,
        )

        self.product2 = Product.objects.create(
            name="Prodotto B",
            slug="prodotto-b",
            category=self.category,
        )

    def test_add_to_cart_creates_item_with_quantity_1(self):
        """
        Aggiungere un prodotto deve inserirlo con quantità 1.
        """
        self.cart.add(self.product1, quantity=1)

        # len(cart) = quantità totale
        self.assertEqual(len(self.cart), 1)

        items = list(self.cart)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["product"], self.product1)
        self.assertEqual(items[0]["quantity"], 1)

    def test_add_same_product_twice_increases_quantity(self):
        """
        Due aggiunte dello stesso prodotto aumentano la quantità:
        - len(cart) = 2 (pezzi totali)
        - ma un solo item con quantity=2
        """
        self.cart.add(self.product1, quantity=1)
        self.cart.add(self.product1, quantity=1)

        # Totale pezzi nel carrello
        self.assertEqual(len(self.cart), 2)

        items = list(self.cart)
        # Un solo item distinto
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["product"], self.product1)
        self.assertEqual(items[0]["quantity"], 2)

    def test_remove_from_cart_removes_item(self):
        """
        Cart.remove deve togliere l'articolo dal carrello.
        """
        self.cart.add(self.product1, quantity=1)
        self.assertEqual(len(self.cart), 1)

        self.cart.remove(self.product1)

        self.assertEqual(len(self.cart), 0)
        # Se hai un metodo is_empty sul Cart, lo testiamo:
        if hasattr(self.cart, "is_empty"):
            self.assertTrue(self.cart.is_empty())

    def test_update_quantity_sets_new_value(self):
        """
        Usare override_quantity=True deve sovrascrivere la quantità.
        """
        self.cart.add(self.product1, quantity=1)
        items = list(self.cart)
        self.assertEqual(items[0]["quantity"], 1)

        self.cart.add(self.product1, quantity=5, override_quantity=True)

        items = list(self.cart)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["product"], self.product1)
        self.assertEqual(items[0]["quantity"], 5)
        # len(cart) = quantità totale
        self.assertEqual(len(self.cart), 5)

    def test_clear_cart_empties_session_cart(self):
        """
        Cart.clear deve svuotare completamente il carrello.
        Nella pratica, dopo clear si istanzia un nuovo Cart(request).
        """
        self.cart.add(self.product1, quantity=2)
        self.cart.add(self.product2, quantity=3)

        # 5 pezzi totali
        self.assertEqual(len(self.cart), 5)

        # Svuota
        self.cart.clear()

        # Nuovo carrello sulla stessa request/session
        new_cart = Cart(self.request)
        self.assertEqual(len(new_cart), 0)
        if hasattr(new_cart, "is_empty"):
            self.assertTrue(new_cart.is_empty())
