from decimal import Decimal
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    """
    Categoria di prodotto/servizio (es. 'Kit biancheria', 'Pulizie', ecc.).
    """
    name = models.CharField("Nome categoria", max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField("Descrizione", blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorie"

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    """
    Prodotto/Servizio venduto sul marketplace.
    Può essere un singolo servizio o un 'kit' composto da più elementi.
    """
    UNIT_PER_KIT = "per_kit"
    UNIT_PER_PIECE = "per_piece"
    UNIT_PER_NIGHT = "per_night"

    UNIT_CHOICES = [
        (UNIT_PER_KIT, "per kit"),
        (UNIT_PER_PIECE, "per pezzo"),
        (UNIT_PER_NIGHT, "per notte"),
    ]

    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    name = models.CharField("Nome prodotto/servizio", max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    short_description = models.CharField("Descrizione breve", max_length=255, blank=True)
    description = models.TextField("Descrizione completa", blank=True)
    is_service = models.BooleanField(
        default=False, help_text="Spunta se è un servizio (no spedizione fisica)."
    )
    supplier = models.ForeignKey(
        "partners.PartnerProfile",
        on_delete=models.PROTECT,
        related_name="products",
        null=True,
        blank=True,
        help_text="Partner che eroga questo prodotto/servizio.",
    )
    base_price = models.DecimalField(
        "Prezzo base", max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    unit = models.CharField(
        "Unità di prezzo", max_length=20, choices=UNIT_CHOICES, default=UNIT_PER_KIT
    )

    main_image = models.ImageField(
        "Immagine principale",
        upload_to="products/main/",
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Prodotto/Servizio"
        verbose_name_plural = "Prodotti/Servizi"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        """
        Genera automaticamente uno slug univoco a partire dal nome
        se non è stato impostato manualmente.
        """
        if not self.slug:
            base_slug = slugify(self.name)
            # fallback nel caso il name sia vuoto per qualche motivo
            if not base_slug:
                base_slug = "product"

            slug = base_slug
            counter = 1

            # Evita duplicati
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/gallery/")
    alt_text = models.CharField("Testo alternativo", max_length=255, blank=True)

    def __str__(self):
        return f"Immagine di {self.product.name}"


class KitComponent(models.Model):
    """
    Componenti di un kit (es. asciugamano piccolo, telo doccia, lenzuola, ecc.).
    """
    kit = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="components",
        limit_choices_to={"is_service": False},
    )
    name = models.CharField("Nome componente", max_length=100)
    quantity = models.PositiveIntegerField("Quantità", default=1)

    class Meta:
        verbose_name = "Componente kit"
        verbose_name_plural = "Componenti kit"

    def __str__(self) -> str:
        return f"{self.name} x{self.quantity} ({self.kit.name})"


class ProductAvailability(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="availabilities"
    )
    date = models.DateField("Data")
    available_quantity = models.PositiveIntegerField("Quantità disponibile", default=0)

    class Meta:
        verbose_name = "Disponibilità prodotto"
        verbose_name_plural = "Disponibilità prodotti"
        unique_together = ("product", "date")
        ordering = ["date"]

    def __str__(self):
        return f"{self.product.name} - {self.date} ({self.available_quantity})"
