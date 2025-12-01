from django.views.generic import TemplateView
from catalog.models import Category, Product


class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Prendi alcune categorie e prodotti da mostrare in home.
        # Puoi aggiungere filtri (es. is_active=True) se il modello li prevede.
        context["categories"] = Category.objects.all()[:6]
        context["featured_products"] = Product.objects.all()[:4]
        return context
