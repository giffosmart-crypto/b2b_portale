from django import forms
from django.contrib.auth import get_user_model

from .models import PartnerProfile

# 👇 IMPORT NECESSARIO PER I PRODOTTI
from catalog.models import Product

User = get_user_model()


class PartnerUserForm(forms.ModelForm):
    """
    Dati anagrafici di base del partner (utente collegato):
    - nome
    - cognome
    - email
    """
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {
            "first_name": "Nome",
            "last_name": "Cognome",
            "email": "Email",
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }


class PartnerProfileForm(forms.ModelForm):
    """
    Dati aziendali del profilo partner:
    - ragione sociale
    - partita IVA
    - indirizzo completo
    - telefono
    """
    class Meta:
        model = PartnerProfile
        fields = [
            "company_name",
            "vat_number",
            "address",
            "city",
            "zip_code",
            "country",
            "phone",
        ]
        labels = {
            "company_name": "Ragione sociale",
            "vat_number": "Partita IVA",
            "address": "Indirizzo",
            "city": "Città",
            "zip_code": "CAP",
            "country": "Paese",
            "phone": "Telefono",
        }
        widgets = {
            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "vat_number": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "zip_code": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
        }


# =============================================================
#   🆕 FORM PRODUCT PER PARTNER (CREA/MODIFICA PRODOTTI)
# =============================================================

class PartnerProductForm(forms.ModelForm):
    """
    Form utilizzato dal partner per creare o modificare un prodotto.
    Il supplier NON è modificabile e verrà settato dalla view.
    """
    class Meta:
        model = Product
        fields = [
            "name",
            "short_description",
            "description",
            "base_price",
            "unit",
            "is_service",
            "category",
            "is_active",
        ]

        labels = {
            "name": "Nome prodotto",
            "short_description": "Descrizione breve",
            "description": "Descrizione completa",
            "base_price": "Prezzo base",
            "unit": "Unità",
            "is_service": "È un servizio?",
            "category": "Categoria",
            "is_active": "Attivo",
        }

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "short_description": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "base_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "unit": forms.Select(attrs={"class": "form-select"}),
            "is_service": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
