# SCOOTER_SHOP/inventory/forms/admin_sales_booking_form.py

from django import forms
from inventory.models import SalesBooking, Motorcycle, SalesProfile
from django.utils.translation import gettext_lazy as _

class AdminSalesBookingForm(forms.ModelForm):
    """
    Form for administrators to create and update SalesBooking instances.
    Allows selection of existing Motorcycle and SalesProfile.
    """
    motorcycle = forms.ModelChoiceField(
        queryset=Motorcycle.objects.all().order_by('brand', 'model', 'year'),
        required=True,
        empty_label=_("-- Select a Motorcycle --"),
        help_text=_("The motorcycle associated with this sales booking."),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    sales_profile = forms.ModelChoiceField(
        queryset=SalesProfile.objects.all().order_by('name', 'email'),
        required=True,
        empty_label=_("-- Select a Sales Profile (Customer) --"),
        help_text=_("The customer's sales profile for this booking."),
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = SalesBooking
        fields = [
            'motorcycle',
            'sales_profile',
            'booking_status',
            'payment_status',
            'amount_paid',
            'currency',
            'request_viewing',
            'appointment_date',
            'appointment_time',
            'customer_notes',
            'stripe_payment_intent_id',
        ]
        widgets = {
            'booking_status': forms.Select(attrs={'class': 'form-control'}),
            'payment_status': forms.Select(attrs={'class': 'form-control'}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'request_viewing': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-indigo-600'}),
            'appointment_date': forms.DateInput(attrs={'class': 'form-control flatpickr-admin-date-input', 'type': 'date'}),
            'appointment_time': forms.TimeInput(attrs={'class': 'form-control flatpickr-admin-time-input', 'type': 'time'}),
            'customer_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'stripe_payment_intent_id': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'booking_status': _("Booking Status"),
            'payment_status': _("Payment Status"),
            'amount_paid': _("Amount Paid"),
            'currency': _("Currency"),
            'request_viewing': _("Requested Viewing/Test Drive"),
            'appointment_date': _("Appointment Date"),
            'appointment_time': _("Appointment Time"),
            'customer_notes': _("Customer Notes"),
            'stripe_payment_intent_id': _("Stripe Payment Intent ID"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add 'form-control' class to all text/number/select inputs by default
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.NumberInput, forms.Select, forms.Textarea, forms.DateInput, forms.TimeInput)) and 'class' not in field.widget.attrs:
                current_classes = field.widget.attrs.get('class', '').split()
                if 'form-control' not in current_classes:
                    current_classes.append('form-control')
                field.widget.attrs['class'] = ' '.join(current_classes)

