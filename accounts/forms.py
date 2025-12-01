from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

from .models import ClientStructure

User = get_user_model()

# ----------------------------------------------------------------------
# Form per le strutture cliente
# ----------------------------------------------------------------------


class ClientStructureForm(forms.ModelForm):
    class Meta:
        model = ClientStructure
        fields = [
            "name",
            "address",
            "city",
            "zip_code",
            "country",
            "phone",
            "is_default_shipping",
        ]


# ----------------------------------------------------------------------
# Form di registrazione utente (cliente / partner)
# ----------------------------------------------------------------------


class CustomUserCreationForm(UserCreationForm):
    """
    Form di registrazione pubblica per CLIENTI e PARTNER.

    Estende il classico UserCreationForm aggiungendo:
    - ruolo (client / partner)
    - email
    - dati aziendali / fatturazione
    """

    ROLE_CHOICES = (
        (User.ROLE_CLIENT, "Cliente"),
        (User.ROLE_PARTNER, "Partner"),
    )

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        label="Tipologia utente",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    email = forms.EmailField(
        label="Email",
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )

    company_name = forms.CharField(
        label="Ragione sociale",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    vat_number = forms.CharField(
        label="Partita IVA",
        max_length=32,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    billing_address = forms.CharField(
        label="Indirizzo fatturazione",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    billing_city = forms.CharField(
        label="Città fatturazione",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    billing_zip = forms.CharField(
        label="CAP fatturazione",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    billing_country = forms.CharField(
        label="Paese fatturazione",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        initial="Italia",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        # Campi base + estensioni B2B
        fields = (
            "username",
            "email",
            "role",
            "company_name",
            "vat_number",
            "billing_address",
            "billing_city",
            "billing_zip",
            "billing_country",
        )

    def save(self, commit: bool = True):
        """
        Salvataggio utente con:
        - password già gestita da UserCreationForm
        - ruolo
        - email
        - dati di fatturazione
        """
        user = super().save(commit=False)

        user.role = self.cleaned_data.get("role", User.ROLE_CLIENT)
        user.email = self.cleaned_data.get("email", "")

        user.company_name = self.cleaned_data.get("company_name", "")
        user.vat_number = self.cleaned_data.get("vat_number", "")
        user.billing_address = self.cleaned_data.get("billing_address", "")
        user.billing_city = self.cleaned_data.get("billing_city", "")
        user.billing_zip = self.cleaned_data.get("billing_zip", "")
        user.billing_country = self.cleaned_data.get("billing_country", "")

        if commit:
            user.save()
            # Qui in futuro potrai creare automaticamente il PartnerProfile per i partner.

        return user


# ----------------------------------------------------------------------
# Form per il profilo utente (CLIENTE / ADMIN)
# ----------------------------------------------------------------------


class ClientProfileForm(forms.ModelForm):
    """
    Modulo per la gestione dei dati anagrafici/fatturazione del cliente
    nella propria area riservata (/my/profile/).
    """

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "company_name",
            "vat_number",

            "billing_address",
            "billing_city",
            "billing_zip",
            "billing_country",

            "phone",
            "sdi_code",
            "pec_email",
        ]
        labels = {
            "first_name": "Nome",
            "last_name": "Cognome",
            "email": "Email",
            "company_name": "Ragione sociale",
            "vat_number": "Partita IVA",

            "billing_address": "Indirizzo fatturazione",
            "billing_city": "Città fatturazione",
            "billing_zip": "CAP fatturazione",
            "billing_country": "Paese fatturazione",

            "phone": "Telefono",
            "sdi_code": "Codice SDI",
            "pec_email": "PEC",
        }


class AdminProfileForm(forms.ModelForm):
    """
    Form per l'amministratore.
    Solo dati anagrafici di base.
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
