from django import forms
from inventory.models.color import Color


class ColorForm(forms.ModelForm):
    class Meta:
        model = Color
        fields = ["name"]
        help_texts = {
            "name": "The name of the color.",
        }
