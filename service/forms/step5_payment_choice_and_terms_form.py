from django import forms
# Assuming ServiceSettings model is in service.models
# You'll need to import ServiceSettings in your forms.py

# Define constants for payment options to avoid magic strings
PAYMENT_OPTION_DEPOSIT = 'deposit_online'
PAYMENT_OPTION_FULL_ONLINE = 'full_online'
PAYMENT_OPTION_INSTORE = 'instore_payment'

class PaymentOptionForm(forms.Form):
    """
    Form for users to select their preferred payment option and accept terms and conditions.
    Payment options are dynamically populated based on ServiceSettings.
    """
    payment_option = forms.ChoiceField(
        label="How would you like to pay?",
        choices=[], # This will be populated dynamically in the __init__ method
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}), # Use RadioSelect for radio buttons
        required=True
    )

    service_terms_accepted = forms.BooleanField(
        label="I agree to the service terms and conditions.",
        required=True, # This checkbox must be checked to proceed
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, service_settings, *args, **kwargs):
        """
        Initializes the form, dynamically populating payment options based on ServiceSettings.
        :param service_settings: The ServiceSettings singleton instance, required to determine
                                 which payment options are enabled.
        """
        super().__init__(*args, **kwargs)

        payment_choices = []

        # Conditionally add payment options based on ServiceSettings
        if service_settings.enable_deposit:
            # Display the deposit amount if it's a flat fee, otherwise indicate calculation
            # FIX: Changed 'flat_fee' to 'FLAT_FEE' to match the model's constant.
            deposit_display = f"Pay Deposit Online ({service_settings.currency_symbol}{service_settings.deposit_flat_fee_amount:.2f})" \
                              if service_settings.deposit_calc_method == 'FLAT_FEE' and service_settings.deposit_flat_fee_amount is not None \
                              else "Pay Deposit Online (calculated)"
            payment_choices.append((PAYMENT_OPTION_DEPOSIT, deposit_display))

        if service_settings.enable_online_full_payment:
            payment_choices.append((PAYMENT_OPTION_FULL_ONLINE, "Pay Full Amount Online Now"))

        if service_settings.enable_instore_full_payment:
            payment_choices.append((PAYMENT_OPTION_INSTORE, "Pay In-Store on Drop-off"))

        # Assign the dynamically generated choices to the payment_option field
        self.fields['payment_option'].choices = payment_choices

        # Optional: If only one payment option is enabled, pre-select it for convenience
        if len(payment_choices) == 1:
            self.fields['payment_option'].initial = payment_choices[0][0]

