from django import forms
from service.models import CustomerMotorcycle, ServiceBrand
from django.utils.translation import gettext_lazy as _


class CustomerMotorcycleForm(forms.ModelForm):
    other_brand_name = forms.CharField(
        label=_("Please specify brand name"),
        required=False,
        max_length=100,
        help_text=_("Required if 'Other' is selected for brand."),
        widget=forms.TextInput,
    )

    brand = forms.ChoiceField(
        label=_("Motorcycle Brand"),
        widget=forms.Select,
        help_text=_(
            "Select the brand of your motorcycle. Choose 'Other' if your brand is not listed. Please note we normally do not work on bike not in the displayed list."
        ),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        brand_names = [
            brand.name for brand in ServiceBrand.objects.all().order_by("name")
        ]

        brand_choices = [("", _("-- Select Brand --"))] + [
            (name, name) for name in brand_names
        ]
        brand_choices.append(("Other", _("Other (please specify)")))

        self.fields["brand"].choices = brand_choices

        if self.instance and self.instance.pk:
            if self.instance.brand in brand_names:
                self.initial["brand"] = self.instance.brand
                self.initial["other_brand_name"] = ""
            else:
                self.initial["brand"] = "Other"
                self.initial["other_brand_name"] = self.instance.brand

    class Meta:
        model = CustomerMotorcycle
        fields = [
            "brand",
            "model",
            "year",
            "engine_size",
            "rego",
            "vin_number",
            "odometer",
            "transmission",
            "engine_number",
        ]
        widgets = {
            "model": forms.TextInput,
            "year": forms.NumberInput,
            "engine_size": forms.TextInput,
            "rego": forms.TextInput,
            "vin_number": forms.TextInput,
            "odometer": forms.NumberInput,
            "transmission": forms.Select,
            "engine_number": forms.TextInput,
        }
        labels = {
            "model": _("Model"),
            "year": _("Year"),
            "engine_size": _("Engine Size (cc)"),
            "rego": _("Registration Number"),
            "vin_number": _("VIN Number"),
            "odometer": _("Odometer Reading (km)"),
            "transmission": _("Transmission Type"),
            "engine_number": _("Engine Number"),
        }

    def clean(self):
        cleaned_data = super().clean()
        brand = cleaned_data.get("brand")
        other_brand_name = cleaned_data.get("other_brand_name")

        if brand == "Other" and not other_brand_name:
            self.add_error(
                "other_brand_name",
                _("Please specify the brand name when 'Other' is selected."),
            )
        elif brand != "Other" and other_brand_name:
            cleaned_data["other_brand_name"] = ""

        return cleaned_data

    def save(self, commit=True):
        brand_from_form = self.cleaned_data["brand"]
        other_brand_name_from_form = self.cleaned_data.get("other_brand_name")
        instance = super().save(commit=False)
        if brand_from_form == "Other" and other_brand_name_from_form:
            instance.brand = other_brand_name_from_form
        if commit:
            instance.save()
            self.save_m2m()
        return instance
