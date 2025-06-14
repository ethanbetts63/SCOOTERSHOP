# SCOOTER_SHOP/inventory/forms/admin_blocked_sales_date_form.py

from django import forms
from inventory.models import BlockedSalesDate
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class AdminBlockedSalesDateForm(forms.ModelForm):
    class Meta:
        model = BlockedSalesDate
        fields = [
            'start_date',
            'end_date',
            'description',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'class': 'form-control flatpickr-admin-date-input', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control flatpickr-admin-date-input', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'start_date': _("Start Date"),
            'end_date': _("End Date"),
            'description': _("Description (Optional)"),
        }
        help_texts = {
            'start_date': _("The first date of the blocked period."),
            'end_date': _("The last date of the blocked period (inclusive)."),
            'description': _("A brief note about why these dates are blocked (e.g., 'Public Holiday', 'Staff Leave')."),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and end_date < start_date:
            raise ValidationError(
                {'end_date': _("End date cannot be before the start date.")}
            )
        return cleaned_data

