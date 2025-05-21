# hire/forms/step5_BookSumAndPaymentOptions_form.py

from django import forms
from dashboard.models import HireSettings
from ..models import TempHireBooking 

class PaymentOptionForm(forms.Form):
    """
    Form to select payment options dynamically based on HireSettings.
    """
    payment_method = forms.ChoiceField(
        label="How would you like to pay?",
        widget=forms.RadioSelect,
        choices=[], 
        help_text="Select your preferred payment method."
    )

    def __init__(self, *args, **kwargs):
        # Expecting 'temp_booking' and 'hire_settings' objects in kwargs
        self.temp_booking = kwargs.pop('temp_booking', None)
        self.hire_settings = kwargs.pop('hire_settings', None)
        super().__init__(*args, **kwargs)

        if not self.hire_settings:
            # Fallback if settings are not provided, though they should be
            self.hire_settings = HireSettings.objects.first()

        self._set_payment_choices()

    def _set_payment_choices(self):
        """
        Dynamically sets the choices for the payment_method field
        based on enabled settings and booking grand total.
        """
        choices = []

        # Online Full Payment
        if self.hire_settings.enable_online_full_payment:
            choices.append(('online_full', 'Pay Full Amount Online Now'))

        # Online Deposit Payment (only if deposit is enabled and grand_total > 0)
        # Note: If grand_total is 0, deposit payment doesn't make sense.
        if self.hire_settings.enable_online_deposit_payment and self.hire_settings.deposit_enabled and self.temp_booking and self.temp_booking.grand_total is not None and self.temp_booking.grand_total > 0:
            # Calculate deposit amount to display
            deposit_display_amount = 0
            if self.hire_settings.default_deposit_calculation_method == 'percentage':
                deposit_display_amount = (self.temp_booking.grand_total * self.hire_settings.deposit_percentage / 100)
            else: 
                deposit_display_amount = self.hire_settings.deposit_amount

            # Ensure deposit amount is not more than grand total
            deposit_display_amount = min(deposit_display_amount, self.temp_booking.grand_total)

            choices.append(
                ('online_deposit',
                 f'Pay Deposit Online Now ({self.hire_settings.currency_symbol}{deposit_display_amount:.2f} due now, remaining at pickup)')
            )

        # In-store Full Payment
        if self.hire_settings.enable_in_store_full_payment:
            choices.append(('in_store_full', 'Pay Full Amount In-Store at Pickup'))

        # Set the choices for the payment_method field
        self.fields['payment_method'].choices = choices

        # Add a custom validator to ensure a choice is made if choices exist
        if choices:
            self.fields['payment_method'].required = True
        else:
            self.fields['payment_method'].required = False

