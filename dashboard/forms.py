# dashboard/forms.py

from django import forms
from django.utils.translation import gettext_lazy as _
import datetime

# Import models from the dashboard app
from .models import AboutPageContent, SiteSettings, BlockedDate, ServiceBrand
from service.models import ServiceType


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
            # Use ClearableFileInput for images to allow removing existing files
            'sales_image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'service_image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'parts_image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }
        # Add labels or help text if needed
        # labels = {
        #     'cta_text': _('Call to Action Text'),
        # }


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
            # Add the google_places_place_id field here
            'google_places_place_id',
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
            'opening_hours_saturday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9:00 AM - 1:00 PM or Closed'}), # Corrected placeholder
            'opening_hours_sunday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Closed'}), # Corrected placeholder
            # Add the widget for the google_places_place_id field
            'google_places_place_id': forms.TextInput(attrs={'class': 'form-control'}),
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
            'enable_google_places_reviews',
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
             'enable_google_places_reviews': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ServiceBookingSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            'allow_anonymous_bookings',
            'allow_account_bookings',
            'booking_open_days',
            'drop_off_start_time',
            'drop_off_end_time',
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
            'drop_off_start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'drop_off_end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'booking_advance_notice': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '30'}),
            'max_visible_slots_per_day': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '24'}),
            'service_confirmation_email_subject': forms.TextInput(attrs={'class': 'form-control'}),
            'service_pending_email_subject': forms.TextInput(attrs={'class': 'form-control'}),
            'admin_service_notification_email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('drop_off_start_time')
        end_time = cleaned_data.get('drop_off_end_time')

        if start_time and end_time and start_time >= end_time:
            self.add_error('drop_off_start_time', _("Booking start time must be earlier than end time."))
            self.add_error('drop_off_end_time', _("Booking end time must be earlier than start time."))


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

        if min_days is not None and max_days is not None and min_days > max_days:
            self.add_error('minimum_hire_duration_days', _("Minimum duration must be less than or equal to maximum duration."))
            self.add_error('maximum_hire_duration_days', _("Maximum duration must be greater than or equal to minimum duration."))


        deposit = cleaned_data.get('default_hire_deposit_percentage')
        if deposit is not None and (deposit < 0 or deposit > 100):
            self.add_error('default_hire_deposit_percentage',
                           _("Deposit percentage must be between 0 and 100."))

        return cleaned_data

class ServiceTypeForm(forms.ModelForm):
    # These fields are for capturing days and hours separately in the form
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
        model = ServiceType # <--- Corrected this line
        fields = ['name', 'description', 'base_price', 'image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        days = cleaned_data.get('estimated_duration_days') or 0
        hours = cleaned_data.get('estimated_duration_hours') or 0

        # Ensure at least one duration field is provided if needed, or allow zero duration
        if days == 0 and hours == 0 and self.instance.pk is None:
             # self.add_error(None, _("Estimated duration (days or hours) is required."))
             pass # Allow zero duration for flexibility

        # Combine days and hours into a timedelta object
        # This calculated value will be assigned to the 'estimated_duration' field on the model instance
        cleaned_data['estimated_duration'] = datetime.timedelta(days=days, hours=hours)

        return cleaned_data

# New form for adding blocked dates
class BlockedDateForm(forms.ModelForm):
    class Meta:
        model = BlockedDate
        fields = ['start_date', 'end_date', 'description']
        widgets = {
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("End date cannot be before the start date.")
        return cleaned_data
    

class ServiceBrandForm(forms.ModelForm):
    class Meta:
        model = ServiceBrand
        fields = ['name', 'image', 'is_primary']
        widgets = {
            # Optional: Add widgets if you want specific HTML attributes, e.g.,
            # 'name': forms.TextInput(attrs={'class': 'my-input-class'}),
        }
        help_texts = {
            'name': "The name of the service brand.",
            'image': "Upload an image for this brand. Required for 'Primary' brands.",
            'is_primary': "Check this box to mark the brand as primary. Requires an image."
        }

    # Add custom validation for the 5 primary brand limit and image requirement
    def clean(self):
        cleaned_data = super().clean()
        is_primary = cleaned_data.get('is_primary')
        image = cleaned_data.get('image')

        # Server-side validation: Primary requires image
        if is_primary and not image:
            # Use add_error for field-specific error
            self.add_error('is_primary', "Primary brands require an image.")
            # Or for a non-field error:
            # raise forms.ValidationError("Primary brands require an image.")


        # Server-side validation: 5 primary brand limit
        # Check the count of existing primary brands *before* saving this one
        # This check is slightly more complex here because it depends on whether
        # the form instance is new or existing (though we are only adding here)
        # Let's refine this check in the view where we know if it's a new object.
        # The view logic will handle the count check based on the form data.

        return cleaned_data
