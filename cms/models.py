from django.conf import settings
from django.db import models


class Page(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField("Titolo", max_length=255)
    body = models.TextField("Contenuto")
    is_published = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Pagina CMS"
        verbose_name_plural = "Pagine CMS"

    def __str__(self) -> str:
        return self.title


class FAQ(models.Model):
    question = models.CharField("Domanda", max_length=255)
    answer = models.TextField("Risposta")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField("Ordine visualizzazione", default=0)

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQ"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.question


class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="newsletter_subscriptions",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Iscrizione newsletter"
        verbose_name_plural = "Iscrizioni newsletter"

    def __str__(self) -> str:
        return self.email


class ContactRequest(models.Model):
    name = models.CharField("Nome", max_length=255)
    email = models.EmailField("Email")
    subject = models.CharField("Oggetto", max_length=255)
    message = models.TextField("Messaggio")
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField("Gestita", default=False)

    class Meta:
        verbose_name = "Richiesta contatto"
        verbose_name_plural = "Richieste contatto"

    def __str__(self) -> str:
        return f"{self.subject} - {self.email}"
