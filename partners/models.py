from django.conf import settings
from django.db import models


class PartnerProfile(models.Model):
    """
    Profilo del Partner (fornitore di servizi/prodotti).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="partner_profile",
        limit_choices_to={"role": "partner"},
    )
    company_name = models.CharField("Ragione sociale", max_length=255)
    vat_number = models.CharField("Partita IVA", max_length=32)
    address = models.CharField("Indirizzo", max_length=255, blank=True)
    city = models.CharField("Città", max_length=100, blank=True)
    zip_code = models.CharField("CAP", max_length=20, blank=True)
    country = models.CharField("Paese", max_length=100, default="Italia")
    phone = models.CharField("Telefono", max_length=50, blank=True)
    default_commission_percent = models.DecimalField(
        "Commissione di default (%)",
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Percentuale di revenue riconosciuta al partner sugli ordini.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Partner"
        verbose_name_plural = "Partner"

    def __str__(self) -> str:
        return self.company_name


# ============================================================
#   🆕 MODELLO NOTIFICHE PARTNER
# ============================================================

class PartnerNotification(models.Model):
    """
    Notifiche interne per il partner.
    Utilizzate per:
    - nuove righe ordine assegnate
    - cambio stato riga
    - messaggi amministrativi
    """

    partner = models.ForeignKey(
        PartnerProfile,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Partner",
    )

    title = models.CharField("Titolo", max_length=255)

    message = models.TextField("Messaggio")

    url = models.CharField(
        "Link di destinazione",
        max_length=255,
        blank=True,
        help_text="URL da aprire quando il partner clicca la notifica (es: dettaglio ordine).",
    )

    is_read = models.BooleanField("Letta", default=False)

    created_at = models.DateTimeField("Data creazione", auto_now_add=True)

    class Meta:
        verbose_name = "Notifica partner"
        verbose_name_plural = "Notifiche partner"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.partner.company_name} - {self.title}"
