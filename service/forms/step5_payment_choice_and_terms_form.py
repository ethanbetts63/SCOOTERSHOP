from django import forms
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal

PAYMENT_OPTION_DEPOSIT = 'online_deposit'
PAYMENT_OPTION_FULL_ONLINE = 'online_full'
PAYMENT_OPTION_INSTORE = 'in_store_full'

class PaymentOptionForm(forms.Form):
    dropoff_date = forms.DateField(
        label="Preferred Drop-off Date",
        widget=forms.DateInput(attrs={'placeholder': 'Select drop-off date'}),
        required=True
    )
    dropoff_time = forms.TimeField(
        label="Preferred Drop-off Time",
        widget=forms.Select,
        required=True
    )
    payment_method = forms.ChoiceField(
        label="How would you like to pay?",
        choices=[],
        widget=forms.RadioSelect,
        required=True
    )
    service_terms_accepted = forms.BooleanField(
        label="I agree to the <a href='#' target='_blank'>service terms and conditions</a>.",
        required=True,
        widget=forms.CheckboxInput
    )

    def __init__(self, *args, **kwargs):
        self.service_settings = kwargs.pop('service_settings')
        self.temp_booking = kwargs.pop('temp_booking')
        super().__init__(*args, **kwargs)
        payment_choices = []
        if self.service_settings.enable_online_deposit and self.service_settings.enable_deposit:
            deposit_display = "Pay Deposit Online"
            if self.service_settings.deposit_calc_method == 'FLAT_FEE' and self.service_settings.deposit_flat_fee_amount is not None:
                deposit_display += f" ({self.service_settings.currency_symbol}{self.service_settings.deposit_flat_fee_amount:.2f})"
            elif self.service_settings.deposit_calc_method == 'PERCENTAGE' and self.service_settings.deposit_percentage is not None:
                deposit_percentage = self.service_settings.deposit_percentage * 100
                deposit_display += f" ({deposit_percentage:.0f}%)"
            payment_choices.append((PAYMENT_OPTION_DEPOSIT, deposit_display))
        if self.service_settings.enable_online_full_payment:
            payment_choices.append((PAYMENT_OPTION_FULL_ONLINE, "Pay Full Amount Online Now"))
        if self.service_settings.enable_instore_full_payment:
            payment_choices.append((PAYMENT_OPTION_INSTORE, "Pay In-Store on Drop-off"))
        self.fields['payment_method'].choices = payment_choices
        if len(payment_choices) == 1:
            self.fields['payment_method'].initial = payment_choices[0][0]

    def clean(self):
        cleaned_data = super().clean()
        dropoff_date = cleaned_data.get('dropoff_date')
        dropoff_time = cleaned_data.get('dropoff_time')
        service_date = self.temp_booking.service_date
        if not all([dropoff_date, dropoff_time, service_date]):
            return cleaned_data
        if dropoff_date > service_date:
            self.add_error('dropoff_date', "Drop-off date cannot be after the service date.")
        max_advance_days = self.service_settings.max_advance_dropoff_days
        earliest_allowed_date = service_date - timedelta(days=max_advance_days)
        if dropoff_date < earliest_allowed_date:
            self.add_error('dropoff_date', f"Drop-off cannot be scheduled more than {max_advance_days} days in advance of the service.")
        today = timezone.localdate(timezone.now())
        if dropoff_date == today:
            latest_time = self.service_settings.latest_same_day_dropoff_time
            if dropoff_time > latest_time:
                self.add_error('dropoff_time', f"For same-day service, drop-off must be no later than {latest_time.strftime('%I:%M %p')}.")
        if dropoff_date == today:
            now_time = timezone.localtime(timezone.now()).time()
            if dropoff_time < now_time:
                self.add_error('dropoff_time', "You cannot select a drop-off time that has already passed today.")
        return cleaned_data
