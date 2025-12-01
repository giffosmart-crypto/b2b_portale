from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404

from datetime import date, timedelta
from .models import Product, Category, ProductAvailability
from partners.models import PartnerProfile


def product_list(request):
    products = Product.objects.filter(is_active=True).select_related("category", "supplier")

    # --- filtri dalla querystring ---
    q = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    partner_id = request.GET.get("partner", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    is_service = request.GET.get("is_service", "").strip()  # "", "1", "0"
    ordering = request.GET.get("ordering", "").strip()

    # --- ricerca full-text semplice ---
    if q:
        products = products.filter(
            Q(name__icontains=q)
            | Q(short_description__icontains=q)
            | Q(description__icontains=q)
            | Q(category__name__icontains=q)
            | Q(supplier__company_name__icontains=q)
        )

    # --- filtro per categoria ---
    if category_slug:
        products = products.filter(category__slug=category_slug)

    # --- filtro per partner/fornitore ---
    if partner_id:
        products = products.filter(supplier_id=partner_id)

    # --- filtri prezzo ---
    if min_price:
        try:
            products = products.filter(base_price__gte=min_price)
        except ValueError:
            pass

    if max_price:
        try:
            products = products.filter(base_price__lte=max_price)
        except ValueError:
            pass

    # --- filtra servizi vs prodotti fisici ---
    if is_service == "1":
        products = products.filter(is_service=True)
    elif is_service == "0":
        products = products.filter(is_service=False)

    # --- ordinamento ---
    if ordering == "price_asc":
        products = products.order_by("base_price")
    elif ordering == "price_desc":
        products = products.order_by("-base_price")
    elif ordering == "name":
        products = products.order_by("name")
    elif ordering == "recent":
        products = products.order_by("-created_at")
    else:
        products = products.order_by("name")

    # --- paginazione ---
    paginator = Paginator(products, 12)  # 12 prodotti per pagina
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # --- dati per i filtri ---
    categories = Category.objects.filter(is_active=True).order_by("name")
    partners = PartnerProfile.objects.filter(is_active=True).order_by("company_name")

    context = {
        "page_obj": page_obj,
        "categories": categories,
        "partners": partners,
        "current_filters": {
            "q": q,
            "category": category_slug,
            "partner": partner_id,
            "min_price": min_price,
            "max_price": max_price,
            "is_service": is_service,
            "ordering": ordering,
        },
    }
    return render(request, "catalog/product_list.html", context)


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category", "supplier").prefetch_related("components"),
        slug=slug,
        is_active=True,
    )
    return render(request, "catalog/product_detail.html", {"product": product})

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
