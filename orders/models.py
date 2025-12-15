from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone
from .utils import get_commission_rate_for_item


class Order(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PENDING_PAYMENT = "pending_payment"
    STATUS_PAID = "paid"
    STATUS_PROCESSING = "processing"
    STATUS_SHIPPED = "shipped"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Bozza"),
        (STATUS_PENDING_PAYMENT, "In attesa pagamento"),
        (STATUS_PAID, "Pagato"),
        (STATUS_PROCESSING, "In lavorazione"),
        (STATUS_SHIPPED, "Spedito"),
        (STATUS_COMPLETED, "Completato"),
        (STATUS_CANCELLED, "Annullato"),
    ]

    PAYMENT_PAYPAL = "paypal"
    PAYMENT_BANK_TRANSFER = "bank_transfer"
    PAYMENT_COD = "cash_on_delivery"

    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_PAYPAL, "PayPal"),
        (PAYMENT_BANK_TRANSFER, "Bonifico bancario"),
        (PAYMENT_COD, "Pagamento alla consegna"),
    ]

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        limit_choices_to={"role": "client"},
    )
    structure = models.ForeignKey(
        "accounts.ClientStructure",
        on_delete=models.PROTECT,
        related_name="orders",
        help_text="Struttura a cui è destinata la merce/servizio.",
    )
    status = models.CharField(
        "Stato ordine", max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING_PAYMENT
    )
    payment_method = models.CharField(
        "Metodo di pagamento",
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default=PAYMENT_BANK_TRANSFER,
    )
    payment_reference = models.CharField(
        "Riferimento pagamento", max_length=255, blank=True
    )
    subtotal = models.DecimalField(
        "Subtotale", max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    shipping_cost = models.DecimalField(
        "Spese di spedizione", max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    total = models.DecimalField(
        "Totale ordine", max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    notes = models.TextField("Note del cliente", blank=True)
    admin_notes = models.TextField("Note amministratore", blank=True)
    invoice_file = models.FileField(
        "Fattura (caricata dall'amministratore)",
        upload_to="invoices/",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    review_invite_sent_at = models.DateTimeField(null=True, blank=True)
    review_reminder_sent_at = models.DateTimeField(null=True, blank=True)
    
    def recalculate_commissions(self):
        """
        Ricalcola le commissioni per tutte le righe dell'ordine
        usando la commissione di default del partner.
        """
        for item in self.items.select_related("partner"):
            if not item.partner:
                continue

            # prendo la % dal profilo partner
            rate = item.partner.default_commission_percent or Decimal("0.00")
            item.commission_rate = rate
            item.calculate_commission(default_rate=rate)
            item.save(update_fields=["commission_rate", "partner_earnings"])

    class Meta:
        verbose_name = "Ordine"
        verbose_name_plural = "Ordini"

    def __str__(self) -> str:
        return f"Ordine #{self.id} - {self.client}"


class OrderItem(models.Model):
    PARTNER_STATUS_PENDING = "pending"
    PARTNER_STATUS_ACCEPTED = "accepted"
    PARTNER_STATUS_IN_PROGRESS = "in_progress"
    PARTNER_STATUS_SHIPPED = "shipped"
    PARTNER_STATUS_COMPLETED = "completed"
    PARTNER_STATUS_REJECTED = "rejected"

    PARTNER_STATUS_CHOICES = [
        (PARTNER_STATUS_PENDING, "In attesa"),
        (PARTNER_STATUS_ACCEPTED, "Accettato"),
        (PARTNER_STATUS_IN_PROGRESS, "In lavorazione"),
        (PARTNER_STATUS_SHIPPED, "Spedito"),
        (PARTNER_STATUS_COMPLETED, "Completato"),
        (PARTNER_STATUS_REJECTED, "Rifiutato"),
    ]

    payout = models.ForeignKey(
        "orders.PartnerPayout",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="items",
    )
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.PROTECT, related_name="order_items"
    )
    partner = models.ForeignKey(
        "partners.PartnerProfile",
        on_delete=models.PROTECT,
        related_name="order_items",
        help_text="Partner al quale è assegnato questo articolo.",
        null=True,
        blank=True,
    )
    quantity = models.PositiveIntegerField("Quantità", default=1)
    unit_price = models.DecimalField("Prezzo unitario", max_digits=10, decimal_places=2)
    total_price = models.DecimalField("Totale riga", max_digits=10, decimal_places=2)

    # 🔹 NUOVI CAMPI COMMISSIONE
    commission_rate = models.DecimalField(
        "Percentuale commissione",
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Percentuale sul totale riga (es. 10 = 10%).",
    )
    
    partner_earnings = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=Decimal("0.00"),
    verbose_name="Importo partner"
    )

    commission_amount = models.DecimalField(
        "Importo commissione",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    partner_status = models.CharField(
        "Stato (partner)",
        max_length=20,
        choices=PARTNER_STATUS_CHOICES,
        default=PARTNER_STATUS_PENDING,
    )
    
    is_liquidated = models.BooleanField(
    "Liquidata",
    default=False,
    help_text="Indica se la commissione di questa riga è già stata liquidata tramite payout."
    )

    class Meta:
        verbose_name = "Riga d'ordine"
        verbose_name_plural = "Righe d'ordine"

    def __str__(self) -> str:
        return f"{self.product} x{self.quantity}"

    # 🔹 METODO DI SUPPORTO
    def calculate_commission(self, default_rate=None):
        """
        Calcola la commissione del portale e il netto partner.

        Priorità della percentuale di commissione:
        1) default_rate passato esplicitamente (se non None)
        2) get_commission_rate_for_item(self.partner, self.product)
        """

        if default_rate is not None:
            rate = default_rate
        else:
            rate = get_commission_rate_for_item(self.partner, self.product)

        # normalizza
        self.commission_rate = rate or Decimal("0.00")

        gross = self.total_price or Decimal("0.00")

        # quota portale
        commission = (gross * self.commission_rate) / Decimal("100.00")
        commission = commission.quantize(Decimal("0.01"))
        self.commission_amount = commission

        # quota partner
        partner_net = gross - commission
        self.partner_earnings = partner_net.quantize(Decimal("0.01"))


# ============================================================
#   🆕 STORICO CAMBI STATO RIGA D'ORDINE (AUDIT LOG)
# ============================================================

class OrderItemStatusLog(models.Model):
    """
    Tiene traccia dei cambi di stato delle righe d'ordine lato partner.
    Ogni volta che cambia partner_status, creiamo una voce di log.
    """

    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name="status_logs",
        verbose_name="Riga d'ordine",
    )

    old_status = models.CharField(
        "Stato precedente",
        max_length=20,
        choices=OrderItem.PARTNER_STATUS_CHOICES,
        blank=True,
        null=True,
        help_text="Stato partner prima della modifica (può essere nullo se è il primo stato).",
    )

    new_status = models.CharField(
        "Nuovo stato",
        max_length=20,
        choices=OrderItem.PARTNER_STATUS_CHOICES,
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orderitem_status_changes",
        verbose_name="Modificato da",
    )

    changed_at = models.DateTimeField(
        "Data modifica",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Log stato riga d'ordine"
        verbose_name_plural = "Log stati righe d'ordine"
        ordering = ["-changed_at"]

    def __str__(self) -> str:
        return f"Riga #{self.order_item_id}: {self.old_status} → {self.new_status} ({self.changed_at:%d/%m/%Y %H:%M})"


# ============================================================
#   🆕 MESSAGGI ORDINE (CLIENTE / PARTNER / ADMIN)
# ============================================================

class OrderMessage(models.Model):
    """
    Messaggistica legata agli ordini:
    - cliente, partner e admin possono scambiarsi messaggi
    - opzionalmente legato a una singola riga d'ordine
    - tracciamo chi l'ha letto (cliente / partner)
    """

    ROLE_CLIENT = "client"
    ROLE_PARTNER = "partner"
    ROLE_ADMIN = "admin"

    ROLE_CHOICES = [
        (ROLE_CLIENT, "Cliente"),
        (ROLE_PARTNER, "Partner"),
        (ROLE_ADMIN, "Admin"),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Ordine",
    )

    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Riga d'ordine",
        null=True,
        blank=True,
        help_text="Opzionale: se il messaggio si riferisce a una riga specifica.",
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_order_messages",
        verbose_name="Mittente",
    )

    sender_role = models.CharField(
        "Ruolo mittente",
        max_length=10,
        choices=ROLE_CHOICES,
    )

    message = models.TextField("Messaggio")

    attachment = models.FileField(
        "Allegato",
        upload_to="order_messages/",
        blank=True,
        null=True,
    )

    # Stati di lettura base (pensati per conversazioni client-partner)
    is_read_by_client = models.BooleanField("Letto dal cliente", default=False)
    is_read_by_partner = models.BooleanField("Letto dal partner", default=False)

    created_at = models.DateTimeField("Creato il", auto_now_add=True)

    class Meta:
        verbose_name = "Messaggio ordine"
        verbose_name_plural = "Messaggi ordine"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Msg ordine #{self.order_id} da {self.sender} ({self.created_at:%d/%m/%Y %H:%M})"
        
class PartnerPayout(models.Model):
    """
    Riepilogo pagamenti delle commissioni verso un partner.
    Non calcola le commissioni (quelle stanno su OrderItem),
    ma le raggruppa per periodo e stato pagamento.
    """

    STATUS_DRAFT = "draft"
    STATUS_CONFIRMED = "confirmed"
    STATUS_PAID = "paid"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Bozza"),
        (STATUS_CONFIRMED, "Confermato"),
        (STATUS_PAID, "Pagato"),
    ]

    partner = models.ForeignKey(
        "partners.PartnerProfile",
        on_delete=models.CASCADE,
        related_name="payouts",
        verbose_name="Partner",
    )

    period_start = models.DateField("Periodo da")
    period_end = models.DateField("Periodo a")

    # 🔹 IMPORTO DA LIQUIDARE AL PARTNER
    total_commission = models.DecimalField(
        "Totale da liquidare al partner",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    status = models.CharField(
        "Stato pagamento",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )

    notes = models.TextField(
        "Note interne",
        blank=True,
    )

    # 🔹 NUOVO CAMPO: ricevuta pagamento
    payment_receipt = models.FileField(
        "Ricevuta di pagamento",
        upload_to="payout_receipts/",
        blank=True,
        null=True,
        help_text="Allega la ricevuta del bonifico o documento contabile.",
    )

    created_at = models.DateTimeField("Creato il", auto_now_add=True)
    updated_at = models.DateTimeField("Aggiornato il", auto_now=True)
    paid_at = models.DateTimeField("Pagato il", null=True, blank=True)

    class Meta:
        verbose_name = "Pagamento partner"
        verbose_name_plural = "Pagamenti partner"
        ordering = ["-period_end", "-created_at"]

    def __str__(self):
        return (
            f"Pagamento {self.partner} "
            f"({self.period_start} → {self.period_end}) - {self.total_commission} €"
        )

    def liquidate_items(self):
        """
        Marca come liquidate tutte le OrderItem del partner
        nel periodo di questo payout.
        """
        from .models import OrderItem  # lasciamo il tuo import locale

        items = OrderItem.objects.filter(
            partner=self.partner,
            order__created_at__date__gte=self.period_start,
            order__created_at__date__lte=self.period_end,
            commission_amount__gt=0,
            is_liquidated=False,
        )

        count = items.count()
        items.update(is_liquidated=True)
        return count

    def save(self, *args, **kwargs):
        """
        Se lo stato passa a PAID:
        - imposta automaticamente paid_at (se non valorizzato)
        - liquida le righe di commissione del periodo per questo partner
        """
        previous_status = None
        if self.pk:
            previous_status = (
                PartnerPayout.objects
                .filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )

        # se da admin imposti direttamente "Pagato" e non c'è paid_at, lo settiamo ora
        if self.status == self.STATUS_PAID and self.paid_at is None:
            self.paid_at = timezone.now()

        super().save(*args, **kwargs)

        # Se prima NON era pagato e ora è pagato → liquida le righe una sola volta
        if previous_status != self.STATUS_PAID and self.status == self.STATUS_PAID:
            self.liquidate_items()
            
            

