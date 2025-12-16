from django import forms
from .models import ProductRating


class ProductRatingForm(forms.ModelForm):
    class Meta:
        model = ProductRating
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "comment": forms.Textarea(attrs={"rows": 3}),
        }
