from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import SiteSettings

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