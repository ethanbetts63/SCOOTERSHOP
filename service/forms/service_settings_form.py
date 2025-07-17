from django import forms
from django.utils.translation import gettext_lazy as _
from ..models import ServiceSettings
from decimal import Decimal


class ServiceBookingSettingsForm(forms.ModelForm):
    class Meta:
        model = ServiceSettings
        fields = [
            "booking_advance_notice",
            "max_visible_slots_per_day",
            "booking_open_days",
            "drop_off_start_time",
            "drop_off_end_time",
            "drop_off_spacing_mins",
            "max_advance_dropoff_days",
            "latest_same_day_dropoff_time",
            "enable_after_hours_dropoff",
            "after_hours_dropoff_disclaimer",
            "after_hours_drop_off_instructions",
            "deposit_calc_method",
            "deposit_flat_fee_amount",
            "deposit_percentage",
            "enable_online_full_payment",
            "enable_online_deposit",
            "enable_instore_full_payment",
            "currency_code",
            "currency_symbol",
        ]
        widgets = {
            "booking_advance_notice": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "max_visible_slots_per_day": forms.NumberInput(
                attrs={"class": "form-control", "min": "1"}
            ),
            "booking_open_days": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Mon,Tue,Wed,Thu,Fri"}
            ),
            "drop_off_start_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "drop_off_end_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "drop_off_spacing_mins": forms.NumberInput(
                attrs={"class": "form-control", "min": "1", "max": "60"}
            ),
            "max_advance_dropoff_days": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "latest_same_day_dropoff_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "enable_after_hours_dropoff": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "after_hours_dropoff_disclaimer": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "after_hours_drop_off_instructions": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "deposit_calc_method": forms.Select(attrs={"class": "form-control"}),
            "deposit_flat_fee_amount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "1"}
            ),
            "deposit_percentage": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "max": "100",
                }
            ),
            "enable_online_full_payment": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_online_deposit": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_instore_full_payment": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "currency_code": forms.TextInput(attrs={"class": "form-control"}),
            "currency_symbol": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()

        start_time = cleaned_data.get("drop_off_start_time")
        end_time = cleaned_data.get("drop_off_end_time")
        latest_same_day_dropoff = cleaned_data.get("latest_same_day_dropoff_time")

        if start_time and end_time and start_time >= end_time:
            self.add_error(
                "drop_off_start_time",
                _("Booking start time must be earlier than end time."),
            )
            self.add_error(
                "drop_off_end_time",
                _("Booking end time must be earlier than start time."),
            )

        drop_off_spacing_mins = cleaned_data.get("drop_off_spacing_mins")
        if drop_off_spacing_mins is not None and (
            drop_off_spacing_mins <= 0 or drop_off_spacing_mins > 60
        ):
            self.add_error(
                "drop_off_spacing_mins",
                _(
                    "Drop-off spacing must be a positive integer, typically between 1 and 60 minutes."
                ),
            )

        max_advance_dropoff_days = cleaned_data.get("max_advance_dropoff_days")
        if max_advance_dropoff_days is not None and max_advance_dropoff_days < 0:
            self.add_error(
                "max_advance_dropoff_days",
                _("Maximum advance drop-off days cannot be negative."),
            )

        if (
            latest_same_day_dropoff
            and start_time
            and end_time
            and (
                latest_same_day_dropoff < start_time
                or latest_same_day_dropoff > end_time
            )
        ):
            self.add_error(
                "latest_same_day_dropoff_time",
                _(
                    f"Latest same-day drop-off time must be between {start_time.strftime('%H:%M')} and {end_time.strftime('%H:%M')}, inclusive."
                ),
            )

        deposit_percentage = cleaned_data.get("deposit_percentage")
        if deposit_percentage is not None and not (
            Decimal("0.00") <= deposit_percentage <= Decimal("100.00")
        ):
            self.add_error(
                "deposit_percentage",
                _("Ensure deposit percentage is between 0.00% and 100.00%."),
            )

        enable_online_deposit = cleaned_data.get("enable_online_deposit")
        deposit_calc_method = cleaned_data.get("deposit_calc_method")
        deposit_flat_fee_amount = cleaned_data.get("deposit_flat_fee_amount")

        if (
            enable_online_deposit
            and deposit_calc_method == "FLAT_FEE"
            and deposit_flat_fee_amount is not None
            and deposit_flat_fee_amount < 1
        ):
            self.add_error(
                "deposit_flat_fee_amount",
                _(
                    "If deposit is enabled as a flat fee, the amount must be at least 1.00."
                ),
            )

        enable_after_hours_dropoff = cleaned_data.get("enable_after_hours_dropoff")
        after_hours_disclaimer = cleaned_data.get("after_hours_dropoff_disclaimer")
        after_hours_instructions = cleaned_data.get("after_hours_drop_off_instructions")

        if enable_after_hours_dropoff:
            if not after_hours_disclaimer:
                self.add_error(
                    "after_hours_dropoff_disclaimer",
                    _("This field is required when after-hours drop-off is enabled."),
                )
            if not after_hours_instructions:
                self.add_error(
                    "after_hours_drop_off_instructions",
                    _("This field is required when after-hours drop-off is enabled."),
                )

        return cleaned_data
