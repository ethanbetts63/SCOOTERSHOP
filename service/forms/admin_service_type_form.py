from django import forms
from service.models import ServiceType
from django.core.exceptions import ValidationError


class AdminServiceTypeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        daily_service_slots = kwargs.pop('daily_service_slots', None)
        super().__init__(*args, **kwargs)
        if daily_service_slots is not None:
            self.fields['slots_required'].help_text = f"How many slots (out of {daily_service_slots} total daily slots) this service consumes."
        else:
            self.fields['slots_required'].help_text = "How many slots this service consumes."

    class Meta:
        model = ServiceType
        fields = [
            "name",
            "description",
            "estimated_duration",
            "base_price",
            "is_active",
            "image",
            "slots_required"
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "estimated_duration": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "(e.g. 1)"}
            ),
            "base_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "image": forms.FileInput(attrs={"class": "form-control-file"}),
            "slots_required": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
        }
        labels = {
            "name": "Service Name",
            "description": "Service Description",
            "estimated_duration": "Estimated Duration",
            "base_price": "Base Price",
            "is_active": "Is Active?",
            "image": "Service Icon/Image",
        }

    def clean_estimated_duration(self):
        estimated_duration = self.cleaned_data.get("estimated_duration")
        if estimated_duration:
            try:
                duration_value = float(estimated_duration)
                if duration_value < 0:
                    raise ValidationError("Estimated duration cannot be negative.")
            except ValueError:
                raise ValidationError("Estimated duration must be a valid number.")
        return estimated_duration

    def clean_base_price(self):
        base_price = self.cleaned_data.get("base_price")
        if base_price is not None:
            if base_price < 0:
                raise ValidationError("Base price cannot be negative.")
        return base_price

    def clean_slots_required(self):
        slots_required = self.cleaned_data.get("slots_required")
        if slots_required is not None:
            if slots_required <= 0:
                raise ValidationError("Slots required must be a positive number.")
        return slots_required
