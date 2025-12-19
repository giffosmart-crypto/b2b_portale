from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.urls import reverse

from accounts.models import User
from catalog.models import Category, Product


class HomeView(TemplateView):
    template_name = "home.html"

    def dispatch(self, request, *args, **kwargs):
        # Se l'utente è autenticato, lo rimandiamo alla sua area (template "standard").
        if request.user.is_authenticated:
            role = getattr(request.user, "role", None)
            if role == User.ROLE_PARTNER:
                return redirect("partners:dashboard")
            if role == User.ROLE_ADMIN:
                return redirect("backoffice:dashboard")
            # default: client / altro -> prima pagina = catalogo
            return redirect("catalog:product_list")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all()[:6]
        context["featured_products"] = Product.objects.all()[:4]
        return context
