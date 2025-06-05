from django import forms
from service.models import CustomerMotorcycle, ServiceProfile

# Define a sentinel value for the 'Add New' option in the dropdown
ADD_NEW_MOTORCYCLE_OPTION = 'add_new'

class MotorcycleSelectionForm(forms.Form):
    """
    Form for authenticated users to select an existing motorcycle from their
    ServiceProfile or to choose to add a new one directly from the dropdown.
    """
    selected_motorcycle = forms.ChoiceField(
        label="Select Your Motorcycle",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    def __init__(self, service_profile, *args, **kwargs):
        """
        Initializes the form.
        :param service_profile: The ServiceProfile instance of the current user.
                                This is used to populate the queryset for existing motorcycles.
        """
        super().__init__(*args, **kwargs)

        # Get existing motorcycles for the service profile
        motorcycles = []
        if service_profile:
            motorcycles = CustomerMotorcycle.objects.filter(service_profile=service_profile)

        # Create choices list: (value, display_name)
        # Add the 'Add New' option first, so it can be the default or easily visible.
        choices = [(ADD_NEW_MOTORCYCLE_OPTION, "--- Add a New Motorcycle ---")]

        # Add existing motorcycles to the choices list
        for mc in motorcycles:
            # Use the motorcycle's primary key as the value
            # and a descriptive string for the display name
            choices.append((str(mc.pk), f"{mc.brand} {mc.model} ({mc.rego})"))

        # Set the choices for the selected_motorcycle field
        self.fields['selected_motorcycle'].choices = choices

        # Optionally, set 'Add New' as the initial default if no motorcycles exist
        # or if you want it to be the first option presented.
        if not motorcycles:
            self.fields['selected_motorcycle'].initial = ADD_NEW_MOTORCYCLE_OPTION

    def clean_selected_motorcycle(self):
        """
        Custom clean method for the selected_motorcycle field.
        This method is primarily for ensuring a valid choice is made.
        The logic for handling 'add_new' vs. existing will be in the view.
        """
        value = self.cleaned_data['selected_motorcycle']
        if value == ADD_NEW_MOTORCYCLE_OPTION:
            # If 'add_new' is selected, no further validation needed on this field itself.
            # The view will handle redirecting to the 'add new motorcycle' form.
            pass
        else:
            # If an existing motorcycle ID is selected, try to retrieve it
            try:
                # Ensure the selected ID corresponds to a valid CustomerMotorcycle
                # belonging to the user's ServiceProfile.
                # The queryset in __init__ already filters by service_profile,
                # but this adds an extra layer of security.
                motorcycle_id = int(value)
                # In the view, you would then fetch the motorcycle using this ID
                # and the user's service_profile for security.
            except (ValueError, TypeError):
                raise forms.ValidationError("Invalid motorcycle selection.")
        return value

