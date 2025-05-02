from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _
from .models import Motorcycle, MotorcycleImage, AboutPageContent, MotorcycleCondition, ServiceType, CustomerMotorcycle, ServiceBooking, SiteSettings
import datetime


class MotorcycleForm(forms.ModelForm):
    class Meta:
        model = Motorcycle
        fields = [
            # Condition first
            'conditions',
            # Basic motorcycle details
            'brand', 'model', 'year', 'price',
            'odometer', 'engine_size',
            # Added required fields
            'seats', 'transmission',
            # Hire rates
            'daily_hire_rate', 'weekly_hire_rate', 'monthly_hire_rate',
            # Other details
            'description', 'image',
            'is_available', 'rego', 'rego_exp', 'stock_number'
        ]
        widgets = {
            'rego_exp': forms.DateInput(attrs={'type': 'date'}),
            'conditions': forms.CheckboxSelectMultiple(attrs={'class': 'condition-checkbox-list'}),
            'daily_hire_rate': forms.NumberInput(attrs={'class': 'hire-field', 'step': '0.01'}),
            'weekly_hire_rate': forms.NumberInput(attrs={'class': 'hire-field', 'step': '0.01'}),
            'monthly_hire_rate': forms.NumberInput(attrs={'class': 'hire-field', 'step': '0.01'}),
            'seats': forms.NumberInput(attrs={'min': '1', 'max': '3'}),
            'transmission': forms.Select(attrs={'class': 'form-control'}),
        }

    title = forms.CharField(required=False)
    engine_size = forms.IntegerField(min_value=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If we have an instance and it has the old condition field but no conditions
        if self.instance and hasattr(self.instance, 'condition') and self.instance.pk and not self.instance.conditions.exists():
            # Try to find matching condition in the new system
            condition_name = self.instance.condition
            condition = MotorcycleCondition.objects.filter(name=condition_name).first()
            if condition:
                # Set initial value for the conditions field based on the old condition
                self.initial['conditions'] = [condition.pk]

    def clean_brand(self):
        # Capitalize the brand name
        return self.cleaned_data['brand'].capitalize()

    def clean_model(self):
        # Capitalize the model name
        return self.cleaned_data['model'].capitalize()

    def clean_rego(self):
        # Convert registration to uppercase if it exists
        if self.cleaned_data['rego']:
            return self.cleaned_data['rego'].upper()
        return self.cleaned_data['rego']

    def clean(self):
        cleaned_data = super().clean()

        # Get selected conditions
        conditions = cleaned_data.get('conditions', [])

        # Define condition names to check for
        new_condition = None
        used_condition = None
        demo_condition = None
        hire_condition = None

        # Check for specific conditions by name
        for condition in conditions:
            if condition.name.lower() == 'new':
                new_condition = condition
            elif condition.name.lower() == 'used':
                used_condition = condition
            elif condition.name.lower() == 'demo':
                demo_condition = condition
            elif condition.name.lower() == 'hire':
                hire_condition = condition

        # If hire condition is selected, daily_hire_rate is required
        if hire_condition and not cleaned_data.get('daily_hire_rate'):
            self.add_error('daily_hire_rate', 'Daily hire rate is required for hire motorcycles')

        # If new, used, or demo condition is selected, price is required
        if (new_condition or used_condition or demo_condition) and not cleaned_data.get('price'):
            self.add_error('price', 'Price is required for motorcycles listed as New, Used, or Demo')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Auto-generate title from year, brand, and model
        instance.title = f"{instance.year} {instance.brand} {instance.model}"

        # If we're using the new conditions field, update the old condition field
        # for backwards compatibility (first condition becomes the primary)
        if 'conditions' in self.cleaned_data and self.cleaned_data['conditions']:
            first_condition = self.cleaned_data['conditions'].first()
            instance.condition = first_condition.name

        if commit:
            instance.save()
            # Save the m2m relations
            self._save_m2m()
        return instance

# Rest of your forms.py remains the same
class MotorcycleImageForm(forms.ModelForm):
    class Meta:
        model = MotorcycleImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'multiple': True
        }

# Create a formset for multiple images
MotorcycleImageFormSet = inlineformset_factory(
    Motorcycle, MotorcycleImage,
    form=MotorcycleImageForm,
    extra=5,  # Show 5 empty forms
    can_delete=True  # Allow deleting existing images
)

class AboutPageContentForm(forms.ModelForm):
    class Meta:
        model = AboutPageContent
        fields = ['intro_text', 'sales_title', 'sales_content', 'sales_image',
                 'service_title', 'service_content', 'service_image',
                 'parts_title', 'parts_content', 'parts_image', 'cta_text']
        widgets = {
            'intro_text': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'sales_content': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'service_content': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'parts_content': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'cta_text': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'sales_title': forms.TextInput(attrs={'class': 'form-control'}),
            'service_title': forms.TextInput(attrs={'class': 'form-control'}),
            'parts_title': forms.TextInput(attrs={'class': 'form-control'}),
            'sales_image': forms.FileInput(attrs={'class': 'form-control'}),
            'service_image': forms.FileInput(attrs={'class': 'form-control'}),
            'parts_image': forms.FileInput(attrs={'class': 'form-control'}),
        }


# Service Booking Forms
class ServiceDetailsForm(forms.Form):
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.filter(is_active=True),
        empty_label="Select a Service Type",
        label="Service Type"
    )
    appointment_datetime = forms.DateTimeField(
        label="Preferred Date and Time",
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )

class CustomerMotorcycleForm(forms.ModelForm):
    class Meta:
        model = CustomerMotorcycle
        fields = ['make', 'model', 'year', 'rego', 'vin_number', 'odometer', 'transmission']
        widgets = {
            'transmission': forms.Select(choices=Motorcycle.TRANSMISSION_CHOICES),
        }

class ServiceBookingUserForm(forms.Form):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=20, required=False)
    preferred_contact = forms.ChoiceField(
        choices=ServiceBooking.CONTACT_CHOICES,
        widget=forms.RadioSelect,
        initial='email'
    )
    booking_comments = forms.CharField(widget=forms.Textarea, required=False)
    is_returning_customer = forms.BooleanField(label="Are you a returning customer?", required=False) # For anonymous users

class ExistingCustomerMotorcycleForm(forms.Form):
    motorcycle = forms.ModelChoiceField(queryset=CustomerMotorcycle.objects.none(), label="Select your Motorcycle")

    def __init__(self, *args, **kwargs):
        # Extract user from kwargs instead of having it as a positional parameter
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set the queryset to show only motorcycles owned by this user
        if user and user.is_authenticated:
            self.fields['motorcycle'].queryset = CustomerMotorcycle.objects.filter(owner_id=user.pk)

class BusinessInfoForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            # Contact information
            'phone_number', 'email_address', 'storefront_address',

            # Business hours
            'opening_hours_monday', 'opening_hours_tuesday', 'opening_hours_wednesday',
            'opening_hours_thursday', 'opening_hours_friday', 'opening_hours_saturday',
            'opening_hours_sunday',
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email_address': forms.EmailInput(attrs={'class': 'form-control'}),
            'storefront_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),

            'opening_hours_monday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9:00 AM - 5:00 PM or Closed'}),
            'opening_hours_tuesday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9:00 AM - 5:00 PM or Closed'}),
            'opening_hours_wednesday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9:00 AM - 5:00 PM or Closed'}),
            'opening_hours_thursday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9:00 AM - 5:00 PM or Closed'}),
            'opening_hours_friday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9:00 AM - 5:00 PM or Closed'}),
            'opening_hours_saturday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9:00 AM - 5:00 PM or Closed'}),
            'opening_hours_sunday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9:00 AM - 5:00 PM or Closed'}),
        }

class VisibilitySettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            'enable_sales_new',
            'enable_sales_used',
            'enable_hire',
            'enable_service_booking',
            'enable_user_accounts',
            'enable_contact_page',
            'enable_about_page',
            'enable_map_display',
            'enable_featured_section',
            'display_new_prices',
            'display_used_prices',
            'enable_privacy_policy_page',
            'enable_returns_page',
            'enable_security_page',
            'enable_terms_page',
        ]
        widgets = {
            'enable_sales_new': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_sales_used': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_hire': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_service_booking': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_user_accounts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_contact_page': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_about_page': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_map_display': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_featured_section': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_new_prices': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_used_prices': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
             'enable_privacy_policy_page': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
             'enable_returns_page': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
             'enable_security_page': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
             'enable_terms_page': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ServiceBookingSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            'allow_anonymous_bookings',
            'allow_account_bookings',
            'booking_open_days',
            'booking_start_time',
            'booking_end_time',
            'booking_advance_notice',
            'max_visible_slots_per_day',
            'service_confirmation_email_subject',
            'service_pending_email_subject',
            'admin_service_notification_email',
        ]
        widgets = {
            'allow_anonymous_bookings': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_account_bookings': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'booking_open_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '365'}),
            'booking_start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'booking_end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'booking_advance_notice': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '30'}),
            'max_visible_slots_per_day': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '24'}),
            'service_confirmation_email_subject': forms.TextInput(attrs={'class': 'form-control'}),
            'service_pending_email_subject': forms.TextInput(attrs={'class': 'form-control'}),
            'admin_service_notification_email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('booking_start_time')
        end_time = cleaned_data.get('booking_end_time')

        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError(
                _("Booking start time must be earlier than end time.")
            )

        return cleaned_data

class HireBookingSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            'minimum_hire_duration_days',
            'maximum_hire_duration_days',
            'hire_booking_advance_notice',
            'default_hire_deposit_percentage',
            'hire_confirmation_email_subject',
            'admin_hire_notification_email',
        ]
        widgets = {
            'minimum_hire_duration_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '30'}),
            'maximum_hire_duration_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '365'}),
            'hire_booking_advance_notice': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '30'}),
            'default_hire_deposit_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '0.01'
            }),
            'hire_confirmation_email_subject': forms.TextInput(attrs={'class': 'form-control'}),
            'admin_hire_notification_email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        min_days = cleaned_data.get('minimum_hire_duration_days')
        max_days = cleaned_data.get('maximum_hire_duration_days')

        if min_days and max_days and min_days > max_days:
            raise forms.ValidationError(
                _("Minimum hire duration must be less than or equal to maximum hire duration.")
            )

        deposit = cleaned_data.get('default_hire_deposit_percentage')
        if deposit and (deposit < 0 or deposit > 100):
            self.add_error('default_hire_deposit_percentage',
                           _("Deposit percentage must be between 0 and 100."))

        return cleaned_data

class ServiceTypeForm(forms.ModelForm):
    estimated_duration_days = forms.IntegerField(
        label="Estimated Duration (Days)",
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0'})
    )
    estimated_duration_hours = forms.IntegerField(
        label="Estimated Duration (Hours)",
        min_value=0,
        max_value=23, # Assuming hours within a day
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '23'})
    )

    class Meta:
        model = ServiceType
        # REMOVE 'estimated_duration' from the fields list
        fields = ['name', 'description', 'base_price', 'image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        days = cleaned_data.get('estimated_duration_days') or 0
        hours = cleaned_data.get('estimated_duration_hours') or 0

        # Combine days and hours into a timedelta object
        # This is correct and will now be used by form.save()
        cleaned_data['estimated_duration'] = datetime.timedelta(days=days, hours=hours)

        return cleaned_data

    # The __init__ method is fine as it handles initial values for the custom fields
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.estimated_duration:
            total_seconds = self.instance.estimated_duration.total_seconds()
            days = int(total_seconds // 86400)
            remaining_seconds = total_seconds % 86400
            hours = int(remaining_seconds // 3600)

            self.initial['estimated_duration_days'] = days
            self.initial['estimated_duration_hours'] = hours

# Rest of your forms.py remains the same
class MiscellaneousSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            # Sales Fields
            'display_new_prices',
            'display_used_prices',
            # Can add more miscellaneous fields here in the future
        ]
        widgets = {
            'display_new_prices': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_used_prices': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }