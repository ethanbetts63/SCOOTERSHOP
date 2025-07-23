from django import forms
import datetime
from inventory.models import Motorcycle


class MotorcycleForm(forms.ModelForm):
    class Meta:
        model = Motorcycle
        fields = [
            "status",
            "conditions",
            "brand",
            "model",
            "year",
            "price",
            "quantity",
            "odometer",
            "engine_size",
            "seats",
            "transmission",
            "description",
            "image",
            "youtube_link",
            "is_available",
            "rego",
            "rego_exp",
            "stock_number",
            "vin_number",
            "engine_number",
            "range",
            "warranty_years",
            "special_text",
        ]
        widgets = {
            "conditions": forms.CheckboxSelectMultiple,
            "rego_exp": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["status"].required = True
        self.fields["conditions"].required = True
        self.fields["price"].required = False
        self.fields["description"].required = False
        self.fields["seats"].required = False
        self.fields["transmission"].required = True
        self.fields["rego"].required = False
        self.fields["rego_exp"].required = False
        self.fields["stock_number"].required = False
        self.fields["brand"].required = True
        self.fields["model"].required = True
        self.fields["vin_number"].required = False
        self.fields["engine_number"].required = False
        self.fields["image"].required = False
        self.fields[
            "image"
        ].help_text = "You can upload images of various file types but please convert to webp. Just google png or jpg to webp and convert your images. webp is much smaller but maintains the same quality so the website will be much faster."
        self.fields["quantity"].required = False
        self.fields["youtube_link"].required = False
        self.fields["year"].required = False
        self.fields["range"].required = False
        self.fields["warranty_years"].required = False
        self.fields["special_text"].required = False

    def clean(self):
        cleaned_data = super().clean()
        brand = cleaned_data.get("brand")
        model = cleaned_data.get("model")
        year = cleaned_data.get("year")
        rego = cleaned_data.get("rego")
        conditions = cleaned_data.get("conditions")
        quantity = cleaned_data.get("quantity")

        if brand:
            cleaned_data["brand"] = brand.capitalize()

        if model:
            cleaned_data["model"] = model.capitalize()

        if year is not None:
            current_year = datetime.date.today().year
            if year < 1885 or year > current_year + 2:
                self.add_error(
                    "year",
                    f"Please enter a valid year between 1885 and {current_year + 2}.",
                )

        if rego:
            cleaned_data["rego"] = rego.upper()

        if conditions:
            condition_names = [c.name for c in conditions]
            is_new = "new" in condition_names
            is_demo = "demo" in condition_names

            if is_new:
                if len(condition_names) > 1:
                    self.add_error(
                        "conditions",
                        "A motorcycle with 'New' condition cannot have other conditions.",
                    )
                if quantity is None or quantity <= 0:
                    self.add_error(
                        "quantity",
                        "Quantity is required and must be a positive number for 'New' motorcycles.",
                    )
            elif is_demo:
                if len(condition_names) > 1:
                    self.add_error(
                        "conditions",
                        "A motorcycle with 'Demo' condition cannot have other conditions.",
                    )
                if quantity is None or quantity <= 0:
                    cleaned_data["quantity"] = 1

            if not is_new and (quantity is None or quantity <= 0):
                cleaned_data["quantity"] = 1

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        parts = []
        if instance.year:
            parts.append(str(instance.year))
        if instance.brand:
            parts.append(instance.brand)
        if instance.model:
            parts.append(instance.model)

        if parts:
            instance.title = " ".join(parts)
        else:
            instance.title = "Untitled Motorcycle"

        if commit:
            instance.save()
            self.save_m2m()

        return instance