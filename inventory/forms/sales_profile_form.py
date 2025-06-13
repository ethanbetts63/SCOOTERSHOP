from django import forms
from inventory.models import SalesProfile, TempSalesBooking

class SalesProfileForm(forms.ModelForm):
    class Meta:
        model = SalesProfile
        fields = [
            'name', 'email', 'phone_number',
            'address_line_1', 'address_line_2', 'city', 'state', 'post_code', 'country',
            'drivers_license_image', 'drivers_license_number', 'drivers_license_expiry',
            'date_of_birth'
        ]
        widgets = {
            'drivers_license_expiry': forms.DateInput(attrs={'type': 'date'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }


    def __init__(self, *args, **kwargs):
        self.inventory_settings = kwargs.pop('inventory_settings', None)
        self.user = kwargs.pop('user', None) # Pass the current user for prefilling
        super().__init__(*args, **kwargs)

        # Prefill for logged-in users with existing SalesProfile
        if self.user and hasattr(self.user, 'sales_profile'):
            sales_profile_instance = self.user.sales_profile
            # Only prefill if the form is not already bound with data
            if not self.is_bound:
                for field in self.fields:
                    if hasattr(sales_profile_instance, field):
                        self.initial[field] = getattr(sales_profile_instance, field)


    def clean(self):
        cleaned_data = super().clean()

        # Conditional validation based on InventorySettings
        if self.inventory_settings:
            if self.inventory_settings.require_address_info:
                required_address_fields = ['address_line_1', 'city', 'post_code', 'country']
                for field_name in required_address_fields:
                    if not cleaned_data.get(field_name):
                        self.add_error(field_name, "This field is required based on inventory settings.")

            if self.inventory_settings.require_drivers_license:
                required_dl_fields = ['drivers_license_number', 'drivers_license_expiry']
                for field_name in required_dl_fields:
                    if not cleaned_data.get(field_name):
                        self.add_error(field_name, "This field is required based on inventory settings.")
                # You might also want to validate drivers_license_image here if needed
                # if not cleaned_data.get('drivers_license_image'):
                #     self.add_error('drivers_license_image', "Driver's license image is required.")

        return cleaned_data