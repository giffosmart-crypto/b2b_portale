from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.urls import reverse
from django.utils import timezone

from orders.models import Order
from catalog.models import ProductRating


def get_products_to_invite_for_order(order: Order):
    """
    Restituisce la lista di prodotti per i quali l'utente NON ha ancora lasciato
    una recensione. Usa ProductRating per verificare.
    """
    products = []
    client = order.client

    # Evitiamo di invitare per righe senza prodotto o senza totale sensato
    for item in order.items.all():
        product = item.product
        if not product:
            continue

        already_rated = ProductRating.objects.filter(
            product=product,
            user=client,
        ).exists()

        if not already_rated:
            products.append(product)

    return products


def _build_product_review_links(products):
    """
    Costruisce una lista di URL (possibilmente assoluti) per la recensione
    di ciascun prodotto.
    """
    links = []
    base_url = getattr(settings, "SITE_BASE_URL", "").rstrip("/")

    for product in products:
        # URL relativa verso la view add_rating
        path = reverse("catalog:add_rating", kwargs={"slug": product.slug})

        # Se abbiamo SITE_BASE_URL in settings, costruiamo URL assoluta
        if base_url:
            url = f"{base_url}{path}"
        else:
            # fallback: URL relativa
            url = path

        links.append(url)

    return links

def _build_review_email_contents(order, products, links, is_reminder=False):
    """
    Costruisce subject, testo e HTML per l'email di invito / reminder recensioni.
    """
    client_name = order.client.first_name or order.client.username or "cliente"

    if is_reminder:
        subject = "Promemoria: lascia una recensione sui prodotti che hai acquistato"
        intro = (
            f"Ciao {client_name},\n\n"
            "qualche giorno fa ti abbiamo inviato un invito a recensire i prodotti che hai acquistato.\n"
            "Se non hai ancora avuto tempo, puoi farlo ora in pochi secondi:\n"
        )
        html_intro = f"""
            <p style="margin:0 0 12px 0;">
                Ciao {client_name},<br/>
                qualche giorno fa ti abbiamo inviato un invito a recensire i prodotti che hai acquistato.<br/>
                Se non hai ancora avuto tempo, puoi farlo ora in pochi secondi:
            </p>
        """
    else:
        subject = "Grazie per il tuo ordine – lascia una recensione"
        intro = (
            f"Ciao {client_name},\n\n"
            "grazie per aver effettuato un ordine sul nostro portale.\n"
            "Ti chiediamo qualche secondo per lasciare una recensione sui prodotti acquistati.\n"
        )
        html_intro = f"""
            <p style="margin:0 0 12px 0;">
                Ciao {client_name},<br/>
                grazie per aver effettuato un ordine sul nostro portale.<br/>
                Ti chiediamo qualche secondo per lasciare una recensione sui prodotti acquistati.
            </p>
        """

    # Corpo testuale (plain text)
    text_lines = [
        intro,
        "",
        "Clicca sui link qui sotto per recensire i singoli prodotti:",
        "",
    ]
    for product, link in zip(products, links):
        text_lines.append(f"- {product.name}: {link}")
    text_lines.append("")
    if is_reminder:
        text_lines.append(
            "Ti invieremo questo promemoria una sola volta, per non disturbarti oltre."
        )
    else:
        text_lines.append(
            "Il tuo feedback è importante per migliorare la qualità del servizio."
        )
    text_lines.append("")
    text_lines.append("Grazie!")
    text_lines.append("Il team del Portale B2B")

    text_body = "\n".join(text_lines)

    # Corpo HTML
    product_items_html = "".join(
        f"""
        <tr>
            <td style="padding:8px 0; font-size:14px; color:#0f172a;">
                {product.name}
            </td>
            <td style="padding:8px 0; text-align:right;">
                <a href="{link}"
                   style="background-color:#0f766e; color:#ffffff; text-decoration:none;
                          padding:8px 14px; border-radius:999px; font-size:13px;">
                    Recensisci
                </a>
            </td>
        </tr>
        """
        for product, link in zip(products, links)
    )

    if is_reminder:
        bottom_message = """
            <p style="font-size:12px; color:#64748b; margin-top:16px;">
                Ti invieremo questo promemoria una sola volta, per non disturbarti oltre.
            </p>
        """
    else:
        bottom_message = """
            <p style="font-size:12px; color:#64748b; margin-top:16px;">
                Il tuo feedback è importante per migliorare la qualità del servizio
                e aiutare altri clienti a scegliere meglio.
            </p>
        """

    html_body = f"""
    <div style="background-color:#e5e7eb; padding:24px 0;">
      <div style="max-width:640px; margin:0 auto; background-color:#ffffff;
                  border-radius:16px; padding:24px 24px 16px 24px;
                  font-family:system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                  color:#0f172a;">
        <!-- Header -->
        <div style="text-align:center; margin-bottom:16px;">
          <div style="font-size:18px; font-weight:600; color:#0f172a;">
            Portale B2B – Recensioni ordine #{order.id}
          </div>
          <div style="font-size:12px; color:#6b7280; margin-top:4px;">
            Aiutaci a migliorare lasciando una recensione sui tuoi acquisti.
          </div>
        </div>

        <!-- Intro -->
        {html_intro}

        <!-- Tabella prodotti -->
        <table style="width:100%; border-collapse:collapse; margin-top:12px;">
          <tbody>
            {product_items_html}
          </tbody>
        </table>

        {bottom_message}

        <p style="font-size:12px; color:#9ca3af; margin-top:16px;">
          Se non desideri più ricevere inviti a recensire i tuoi acquisti,
          puoi ignorare questo messaggio.
        </p>

        <p style="font-size:11px; color:#9ca3af; margin-top:8px;">
          Questo messaggio è stato generato automaticamente, ti preghiamo di non rispondere a questa email.
        </p>
      </div>
    </div>
    """

    return subject, text_body, html_body


def send_review_invite(order: Order):
    """
    Invia il PRIMO invito recensione per un ordine completato.
    Non si occupa di reminder (gestito separatamente).
    """
    products = get_products_to_invite_for_order(order)
    if not products:
        return False  # niente da recensire

    links = _build_product_review_links(products)

    subject, text_body, html_body = _build_review_email_contents(
        order=order,
        products=products,
        links=links,
        is_reminder=False,
    )

    from_email = getattr(
        settings,
        "DEFAULT_FROM_EMAIL",
        "noreply@portale-b2b.local",
    )
    recipient = order.client.email
    if not recipient:
        return False  # niente email da usare

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=[recipient],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=True)

    # Aggiorniamo il timestamp sul modello ordine
    order.review_invite_sent_at = timezone.now()
    order.save(update_fields=["review_invite_sent_at"])

    return True


def send_review_reminder(order: Order):
    """
    Invia UN SOLO reminder se l'utente non ha ancora recensito tutto.
    """
    products = get_products_to_invite_for_order(order)
    if not products:
        return False  # nulla da ricordare

    links = _build_product_review_links(products)

    subject, text_body, html_body = _build_review_email_contents(
        order=order,
        products=products,
        links=links,
        is_reminder=True,
    )

    from_email = getattr(
        settings,
        "DEFAULT_FROM_EMAIL",
        "noreply@portale-b2b.local",
    )
    recipient = order.client.email
    if not recipient:
        return False

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=[recipient],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=True)

    order.review_reminder_sent_at = timezone.now()
    order.save(update_fields=["review_reminder_sent_at"])

    return True


def get_orders_for_first_invite(reference_time=None):
    """
    Restituisce gli ordini per cui mandare il PRIMO invito.

    Criteri:
    - status = completed
    - review_invite_sent_at è NULL
    - creati da almeno 2 giorni
    - creati da non più di 30 giorni (per evitare ordini vecchissimi)
    """
    if reference_time is None:
        reference_time = timezone.now()

    from_time = reference_time - timedelta(days=30)
    to_time = reference_time - timedelta(days=2)

    return Order.objects.filter(
        status=Order.STATUS_COMPLETED,
        created_at__range=(from_time, to_time),
        review_invite_sent_at__isnull=True,
    )


def get_orders_for_reminder(reference_time=None):
    """
    Restituisce gli ordini per cui mandare il REMINDER.

    Criteri:
    - status = completed
    - review_invite_sent_at non null
    - review_reminder_sent_at è NULL
    - l'invito è stato inviato da almeno 7 giorni
    """
    if reference_time is None:
        reference_time = timezone.now()

    cutoff = reference_time - timedelta(days=7)

    return Order.objects.filter(
        status=Order.STATUS_COMPLETED,
        review_invite_sent_at__lte=cutoff,
        review_reminder_sent_at__isnull=True,
    )
