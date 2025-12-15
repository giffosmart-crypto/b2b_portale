from decimal import Decimal
from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.db.models import Avg


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
    
    partner_commission_rate = models.DecimalField(
        "Commissione specifica prodotto (%)",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Se valorizzato, questo valore viene usato come commissione "
            "per questo prodotto (priorità più alta)."
        ),
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
    
    @property
    def average_rating(self):
        """
        Rating medio del prodotto calcolato SOLO sulle recensioni approvate.
        """
        qs = self.ratings.filter(is_approved=True)
        result = qs.aggregate(avg=Avg("rating"))["avg"]
        return result or 0

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
        
        
class ProductRating(models.Model):
    # Stati di moderazione
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    MODERATION_STATUS_CHOICES = [
        (STATUS_PENDING, "In attesa"),
        (STATUS_APPROVED, "Approvata"),
        (STATUS_REJECTED, "Rifiutata"),
    ]

    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="product_ratings",
    )
    rating = models.PositiveSmallIntegerField()  # 1–5
    comment = models.TextField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Flag storico ancora usato nel resto del codice (average_rating, ecc.)
    # D'ora in poi viene tenuto allineato allo stato di moderazione.
    is_approved = models.BooleanField(
        default=False,
        help_text="True se la recensione è approvata e visibile.",
    )

    # Nuovo stato di moderazione a 3 livelli
    moderation_status = models.CharField(
        max_length=20,
        choices=MODERATION_STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        help_text="Stato della moderazione: in attesa / approvata / rifiutata.",
    )
    
    # Audit moderazione
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="moderated_ratings",
        help_text="Utente staff che ha effettuato l'ultima moderazione.",
    )
    moderated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data/ora dell'ultima moderazione.",
    )

    class Meta:
        unique_together = ("product", "user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product} - {self.user} ({self.rating})"

    # --- Helper comodi per admin e template ---

    @property
    def is_pending(self) -> bool:
        return self.moderation_status == self.STATUS_PENDING

    @property
    def is_rejected(self) -> bool:
        return self.moderation_status == self.STATUS_REJECTED

    @property
    def status_label(self) -> str:
        """
        Etichetta leggibile per lo stato (per template/admin).
        """
        mapping = dict(self.MODERATION_STATUS_CHOICES)
        return mapping.get(self.moderation_status, "")


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
