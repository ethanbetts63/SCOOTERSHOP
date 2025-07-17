from django import forms
from inventory.models import FeaturedMotorcycle


class FeaturedMotorcycleForm(forms.ModelForm):
    class Meta:
        model = FeaturedMotorcycle
        fields = ["motorcycle", "category", "order"]
        widgets = {
            "motorcycle": forms.HiddenInput(),
            "category": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        """
        Initializes the form. No special queryset filtering is needed anymore
        as the motorcycle is selected via an AJAX search.
        """
        super().__init__(*args, **kwargs)
        # The 'order' field can be styled or have attributes set here if needed
        self.fields["order"].widget.attrs.update(
            {"class": "form-control w-full p-2 border rounded-md"}
        )

    def clean_motorcycle(self):
        """
        Custom validation for the motorcycle field to ensure it's not empty.
        """
        motorcycle = self.cleaned_data.get("motorcycle")
        if not motorcycle:
            raise forms.ValidationError("You must select a motorcycle.")
        return motorcycle
