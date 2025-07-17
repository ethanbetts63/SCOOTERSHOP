from django import forms

PAYMENT_OPTION_DEPOSIT = "online_deposit"
PAYMENT_OPTION_FULL_ONLINE = "online_full"
PAYMENT_OPTION_INSTORE = "in_store_full"


class PaymentOptionForm(forms.Form):
    dropoff_date = forms.DateField(
        label="Preferred Drop-off Date",
        widget=forms.DateInput(attrs={"placeholder": "Select drop-off date"}),
        required=True,
    )
    dropoff_time = forms.TimeField(
        label="Preferred Drop-off Time", widget=forms.Select, required=False
    )
    payment_method = forms.ChoiceField(
        label="How would you like to pay?",
        choices=[],
        widget=forms.RadioSelect,
        required=True,
    )
    service_terms_accepted = forms.BooleanField(
        label="I agree to the <a href='#' target='_blank'>service terms and conditions</a>.",
        required=True,
        widget=forms.CheckboxInput,
    )
    after_hours_drop_off_choice = forms.BooleanField(
        label="Opt for After-Hours Drop-Off",
        required=False,
        widget=forms.CheckboxInput,
        help_text="Select this if you intend to use our 24/7 key drop-off box."
    )

    def __init__(self, *args, **kwargs):
        self.service_settings = kwargs.pop("service_settings")
        self.temp_booking = kwargs.pop("temp_booking")
        super().__init__(*args, **kwargs)
        payment_choices = []
        if (
            self.service_settings.enable_online_deposit
        ):
            deposit_display = "Pay Deposit Online"
            if (
                self.service_settings.deposit_calc_method == "FLAT_FEE"
                and self.service_settings.deposit_flat_fee_amount is not None
            ):
                deposit_display += f" ({self.service_settings.currency_symbol}{self.service_settings.deposit_flat_fee_amount:.2f})"
            elif (
                self.service_settings.deposit_calc_method == "PERCENTAGE"
                and self.service_settings.deposit_percentage is not None
            ):
                deposit_percentage = self.service_settings.deposit_percentage * 100
                deposit_display += f" ({deposit_percentage:.0f}%)"
            payment_choices.append((PAYMENT_OPTION_DEPOSIT, deposit_display))
        if self.service_settings.enable_online_full_payment:
            payment_choices.append(
                (PAYMENT_OPTION_FULL_ONLINE, "Pay Full Amount Online Now")
            )
        if self.service_settings.enable_instore_full_payment:
            payment_choices.append((PAYMENT_OPTION_INSTORE, "Pay In-Store on Drop-off"))
        self.fields["payment_method"].choices = payment_choices
        if len(payment_choices) == 1:
            self.fields["payment_method"].initial = payment_choices[0][0]

        if not self.service_settings.enable_after_hours_dropoff:
            del self.fields['after_hours_drop_off_choice']

    def clean(self):
        cleaned_data = super().clean()
        after_hours_drop_off = cleaned_data.get('after_hours_drop_off_choice')
        dropoff_time = cleaned_data.get('dropoff_time')

        if not after_hours_drop_off and not dropoff_time:
            self.add_error('dropoff_time', 'This field is required if you are not using the after-hours drop-off.')

        if after_hours_drop_off and dropoff_time:
            self.add_error('dropoff_time', 'Please do not select a time if you are using the after-hours drop-off.')
        
        return cleaned_data
