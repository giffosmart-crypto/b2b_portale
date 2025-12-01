
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Utente unico per tutti i ruoli del marketplace:
    - admin (amministratore della piattaforma)
    - partner (fornitore)
    - client (gestore Hotel/B&B/Casa vacanze)
    """
    ROLE_ADMIN = "admin"
    ROLE_PARTNER = "partner"
    ROLE_CLIENT = "client"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "Amministratore"),
        (ROLE_PARTNER, "Partner"),
        (ROLE_CLIENT, "Cliente"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CLIENT)

    # Dati aziendali / fiscali
    company_name = models.CharField("Ragione sociale", max_length=255, blank=True)
    vat_number = models.CharField("Partita IVA", max_length=32, blank=True)

    # Dati di fatturazione
    billing_address = models.CharField("Indirizzo fatturazione", max_length=255, blank=True)
    billing_city = models.CharField("Città fatturazione", max_length=100, blank=True)
    billing_zip = models.CharField("CAP fatturazione", max_length=20, blank=True)
    billing_country = models.CharField("Paese fatturazione", max_length=100, blank=True)

    # Contatti e fatturazione elettronica
    sdi_code = models.CharField("Codice SDI", max_length=20, blank=True)
    pec_email = models.EmailField("PEC", max_length=255, blank=True)
    phone = models.CharField("Telefono", max_length=50, blank=True)

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        """
        Salva l'utente e sincronizza TUTTE le strutture collegate
        (indirizzo, città, CAP, paese, telefono) se l'utente è un CLIENT.

        Opzione 4: sincronizzazione completa su tutte le strutture.
        """
        super().save(*args, **kwargs)

        # Sincronizza solo per i clienti
        if self.role == self.ROLE_CLIENT:
            # Import "lazy": ClientStructure è definita più sotto nello stesso file
            from .models import ClientStructure  # type: ignore

            # Valori da propagare alle strutture
            addr = self.billing_address or ""
            city = self.billing_city or ""
            cap = self.billing_zip or ""
            country = self.billing_country or "Italia"
            phone = self.phone or ""

            ClientStructure.objects.filter(owner=self).update(
                address=addr,
                city=city,
                zip_code=cap,
                country=country,
                phone=phone,
            )


class ClientStructure(models.Model):
    """
    Strutture gestite dal Cliente (Hotel, B&B, Casa Vacanze).
    Servono anche come indirizzi di spedizione.
    """
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="structures",
        limit_choices_to={"role": User.ROLE_CLIENT},
    )
    name = models.CharField("Nome struttura", max_length=255)
    address = models.CharField("Indirizzo", max_length=255)
    city = models.CharField("Città", max_length=100)
    zip_code = models.CharField("CAP", max_length=20)
    country = models.CharField("Paese", max_length=100, default="Italia")
    phone = models.CharField("Telefono", max_length=50, blank=True)
    is_default_shipping = models.BooleanField(
        "Usa come indirizzo di spedizione predefinito", default=False
    )

    class Meta:
        verbose_name = "Struttura Cliente"
        verbose_name_plural = "Strutture Clienti"

    def __str__(self) -> str:
        return f"{self.name} - {self.city}"

    def save(self, *args, **kwargs):
        """
        Alla creazione/modifica, se qualche campo indirizzo è vuoto,
        viene precompilato con i dati di fatturazione del profilo utente.
        Questo rende coerente la sincronizzazione completa (Opzione 4).
        """
        if self.owner and self.owner.role == User.ROLE_CLIENT:
            # Precompila solo i campi vuoti
            if not self.address and self.owner.billing_address:
                self.address = self.owner.billing_address
            if not self.city and self.owner.billing_city:
                self.city = self.owner.billing_city
            if not self.zip_code and self.owner.billing_zip:
                self.zip_code = self.owner.billing_zip
            if not self.country and self.owner.billing_country:
                self.country = self.owner.billing_country
            if not self.phone and self.owner.phone:
                self.phone = self.owner.phone

        super().save(*args, **kwargs)
