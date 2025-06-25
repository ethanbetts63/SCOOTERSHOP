from django import forms
from service.models import CustomerMotorcycle, ServiceProfile

ADD_NEW_MOTORCYCLE_OPTION = 'add_new'

class MotorcycleSelectionForm(forms.Form):
    selected_motorcycle = forms.ChoiceField(
        label="Select Your Motorcycle",
        widget=forms.Select,
        required=True
    )

    def __init__(self, service_profile, *args, **kwargs):
        super().__init__(*args, **kwargs)
        motorcycles = []
        if service_profile:
            motorcycles = CustomerMotorcycle.objects.filter(service_profile=service_profile)

        choices = [(ADD_NEW_MOTORCYCLE_OPTION, "--- Add a New Motorcycle ---")]
        for mc in motorcycles:
            choices.append((str(mc.pk), f"{mc.brand} {mc.model} ({mc.rego})"))

        self.fields['selected_motorcycle'].choices = choices

        if not motorcycles:
            self.fields['selected_motorcycle'].initial = ADD_NEW_MOTORCYCLE_OPTION

    def clean_selected_motorcycle(self):
        value = self.cleaned_data['selected_motorcycle']
        if value != ADD_NEW_MOTORCYCLE_OPTION:
            try:
                motorcycle_id = int(value)
            except (ValueError, TypeError):
                raise forms.ValidationError("Invalid motorcycle selection.")
        return value
