
from django.db.models import Q, Avg
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib import messages

from orders.models import OrderItem

from .forms import ProductRatingForm

from datetime import date, timedelta
from .models import Product, Category, ProductAvailability, ProductRating
from partners.models import PartnerProfile


def product_list(request):
    """
    Catalogo prodotti con:
    - filtri per categoria, partner, testo
    - ordinamento per rating (premialità) / prezzo / nome
    - liste categorie e partner per i filtri

    Il rating medio è calcolato SOLO sulle recensioni approvate.
    """

    # Query base: prodotti attivi
    qs = Product.objects.filter(is_active=True)

    # --- FILTRI ---

    category_id = request.GET.get("category")
    if category_id:
        qs = qs.filter(category_id=category_id)

    partner_id = request.GET.get("partner")
    if partner_id:
        qs = qs.filter(supplier_id=partner_id)

    search = request.GET.get("q")
    if search:
        qs = qs.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    # --- ANNOTAZIONE RATING MEDIO SOLO DA RECENSIONI APPROVATE ---
    qs = qs.annotate(
        avg_rating=Avg(
            "ratings__rating",
            filter=Q(ratings__is_approved=True),
        )
    )

    # --- ORDINAMENTO ---

    sort = request.GET.get("sort", "rating")
    if sort == "price_asc":
        qs = qs.order_by("base_price")
    elif sort == "price_desc":
        qs = qs.order_by("-base_price")
    elif sort == "name":
        qs = qs.order_by("name")
    else:
        # default: premialità → prima rating più alto, poi nome
        qs = qs.order_by("-avg_rating", "name")

    # --- PAGINAZIONE ---

    paginator = Paginator(qs, 20)
    page = request.GET.get("page")
    products = paginator.get_page(page)

    # --- DATI PER I FILTRI ---

    categories = Category.objects.all().order_by("name")
    partners = PartnerProfile.objects.all().order_by("company_name")

    context = {
        "products": products,
        "categories": categories,
        "partners": partners,
        "selected_category": int(category_id) if category_id else None,
        "selected_partner": int(partner_id) if partner_id else None,
        "search": search or "",
        "sort": sort,
    }
    return render(request, "catalog/product_list.html", context)


def product_detail(request, slug):
    """
    Dettaglio prodotto:
    - mostra SOLO recensioni approvate
    - rating medio coerente (usa Product.average_rating che filtra già is_approved=True)
    """
    product = get_object_or_404(Product, slug=slug, is_active=True)

    # Recensioni approvate, paginate (ordine dal più recente)
    review_qs = product.ratings.filter(is_approved=True).order_by("-created_at")
    paginator = Paginator(review_qs, 10)
    page = request.GET.get("page")
    reviews = paginator.get_page(page)

    user_review = None
    has_bought = False

    if request.user.is_authenticated:
        # eventuale recensione già inserita dall'utente (qualsiasi stato)
        user_review = product.ratings.filter(user=request.user).first()

        # verifica che l'utente abbia acquistato il prodotto
        has_bought = OrderItem.objects.filter(
            order__client=request.user,
            product=product,
            order__status="completed",
        ).exists()

    context = {
        "product": product,
        "reviews": reviews,
        "user_review": user_review,
        "has_bought": has_bought,
    }
    return render(request, "catalog/product_detail.html", context)


def product_availability(request, slug):
    product = get_object_or_404(
        Product.objects.prefetch_related("availabilities"),
        slug=slug,
        is_active=True,
    )

    today = date.today()
    end_date = today + timedelta(days=30)

    availabilities = (
        ProductAvailability.objects
        .filter(product=product, date__range=(today, end_date))
        .order_by("date")
    )

    return render(
        request,
        "catalog/product_availability.html",
        {
            "product": product,
            "availabilities": availabilities,
            "start_date": today,
            "end_date": end_date,
        },
    )


@login_required
def add_rating(request, slug):
    """
    Creazione/modifica recensione utente:
    - consentita solo a chi ha acquistato il prodotto (ordine completed)
    - l'utente può modificare la propria recensione SOLO finché è in attesa
    - ogni salvataggio mette la recensione in stato 'pending' e non approvata
    """

    # prodotto deve esistere ed essere attivo
    product = get_object_or_404(Product, slug=slug, is_active=True)

    # sicurezza: consenti la recensione solo a chi ha completato almeno un ordine
    has_bought = OrderItem.objects.filter(
        order__client=request.user,
        product=product,
        order__status="completed",
    ).exists()

    if not has_bought:
        return HttpResponseForbidden(
            "Non puoi recensire un prodotto che non hai acquistato."
        )

    # se l'utente ha già recensito il prodotto, carichiamo l'istanza esistente
    instance = ProductRating.objects.filter(
        product=product,
        user=request.user,
    ).first()

    # Se la recensione è già stata moderata, non consentiamo ulteriori modifiche
    if instance and instance.moderation_status != ProductRating.STATUS_PENDING:
        messages.info(
            request,
            "La tua recensione è già stata moderata e non può essere modificata.",
        )
        return redirect("catalog:product_detail", slug=product.slug)

    if request.method == "POST":
        form = ProductRatingForm(request.POST, instance=instance)
        if form.is_valid():
            rating_obj = form.save(commit=False)
            rating_obj.product = product
            rating_obj.user = request.user

            # Ogni invio/metà modifica passa SEMPRE per la moderazione:
            rating_obj.is_approved = False
            rating_obj.moderation_status = ProductRating.STATUS_PENDING
            # reset audit (sarà popolato al momento della moderazione)
            if hasattr(rating_obj, "moderated_by"):
                rating_obj.moderated_by = None
            if hasattr(rating_obj, "moderated_at"):
                rating_obj.moderated_at = None

            rating_obj.save()

            messages.success(
                request,
                "La tua recensione è stata inviata e sarà visibile dopo approvazione dello staff.",
            )
            return redirect("catalog:product_detail", slug=product.slug)
    else:
        form = ProductRatingForm(instance=instance)

    return render(
        request,
        "catalog/add_rating.html",
        {"product": product, "form": form},
    )
