from django import forms
from accounts.models import ClientStructure
from .models import Order


class CheckoutForm(forms.Form):
    structure = forms.ModelChoiceField(
        queryset=ClientStructure.objects.none(),
        label="Struttura di consegna",
        help_text="Seleziona la struttura a cui è destinato l'ordine.",
    )
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_METHOD_CHOICES,
        label="Metodo di pagamento",
    )
    notes = forms.CharField(
        label="Note aggiuntive",
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["structure"].queryset = ClientStructure.objects.filter(
                owner=user
            )
