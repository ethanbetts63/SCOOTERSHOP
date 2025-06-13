from django import forms
from inventory.models import SalesProfile, TempSalesBooking # Ensure TempSalesBooking is imported

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
            # Added 'text-gray-900' for dark text color
            'name': forms.TextInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 text-gray-900'}),
            'email': forms.EmailInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 text-gray-900'}),
            'phone_number': forms.TextInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 text-gray-900'}),
            'address_line_1': forms.TextInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 text-gray-900'}),
            'address_line_2': forms.TextInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 text-gray-900'}),
            'city': forms.TextInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 text-gray-900'}),
            'state': forms.TextInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 text-gray-900'}),
            'post_code': forms.TextInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 text-gray-900'}),
            'country': forms.TextInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 text-gray-900'}),
            'drivers_license_image': forms.ClearableFileInput(attrs={'class': 'mt-1 block w-full text-sm text-gray-900 border border-gray-300 rounded-md cursor-pointer bg-gray-50 focus:outline-none'}), # text-gray-900 already here
            'drivers_license_number': forms.TextInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 text-gray-900'}),
            'drivers_license_expiry': forms.DateInput(attrs={'type': 'date', 'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 text-gray-900'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 text-gray-900'}),
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

        # Apply required attribute based on inventory settings for address and DL fields
        if self.inventory_settings:
            if self.inventory_settings.require_address_info:
                for field_name in ['address_line_1', 'city', 'post_code', 'country']:
                    self.fields[field_name].required = True
                    self.fields[field_name].widget.attrs.update({'placeholder': 'Required'})
            else:
                # If address not required, ensure these fields are not required by default
                for field_name in ['address_line_1', 'address_line_2', 'city', 'state', 'post_code', 'country']:
                    self.fields[field_name].required = False

            if self.inventory_settings.require_drivers_license:
                for field_name in ['drivers_license_number', 'drivers_license_expiry', 'drivers_license_image']:
                    self.fields[field_name].required = True
                    self.fields[field_name].widget.attrs.update({'placeholder': 'Required'})
                self.fields['date_of_birth'].required = True # DOB is also required with DL
            else:
                # If DL not required, ensure these fields are not required by default
                for field_name in ['drivers_license_number', 'drivers_license_expiry', 'drivers_license_image', 'date_of_birth']:
                    self.fields[field_name].required = False


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
                if self.inventory_settings.require_drivers_license and not cleaned_data.get('drivers_license_image'):
                    self.add_error('drivers_license_image', "Driver's license image is required based on inventory settings.")
                if self.inventory_settings.require_drivers_license and not cleaned_data.get('date_of_birth'):
                    self.add_error('date_of_birth', "Date of birth is required based on inventory settings.")

        return cleaned_data
