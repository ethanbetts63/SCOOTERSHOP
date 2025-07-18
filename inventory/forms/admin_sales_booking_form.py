from django import forms
from inventory.models import SalesBooking, Motorcycle, SalesProfile, InventorySettings
from django.utils.translation import gettext_lazy as _
from datetime import date
from django.utils import timezone
from decimal import Decimal


class AdminSalesBookingForm(forms.ModelForm):
    selected_profile_id = forms.IntegerField(
        required=True, widget=forms.HiddenInput(), label=_("Selected Sales Profile ID")
    )
    selected_motorcycle_id = forms.IntegerField(
        required=True, widget=forms.HiddenInput(), label=_("Selected Motorcycle ID")
    )

    class Meta:
        model = SalesBooking
        fields = [
            "booking_status",
            "payment_status",
            "amount_paid",
            "currency",
            "appointment_date",
            "appointment_time",
            "customer_notes",
        ]
        widgets = {
            "booking_status": forms.Select(attrs={"class": "form-control"}),
            "payment_status": forms.Select(attrs={"class": "form-control"}),
            "amount_paid": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "currency": forms.TextInput(attrs={"class": "form-control"}),
            "appointment_date": forms.DateInput(
                attrs={
                    "class": "form-control flatpickr-admin-date-input",
                    "type": "date",
                }
            ),
            "appointment_time": forms.TimeInput(
                attrs={
                    "class": "form-control flatpickr-admin-time-input",
                    "type": "time",
                }
            ),
            "customer_notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }
        labels = {
            "booking_status": _("Booking Status"),
            "payment_status": _("Payment Status"),
            "amount_paid": _("Amount Paid"),
            "currency": _("Currency"),
            "appointment_date": _("Appointment Date"),
            "appointment_time": _("Appointment Time"),
            "customer_notes": _("Customer Notes"),
        }

    def __init__(self, *args, **kwargs):
        self.initial_sales_profile = kwargs.pop("initial_sales_profile", None)
        self.initial_motorcycle = kwargs.pop("initial_motorcycle", None)
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            if (
                isinstance(
                    field.widget,
                    (
                        forms.TextInput,
                        forms.NumberInput,
                        forms.Select,
                        forms.Textarea,
                        forms.DateInput,
                        forms.TimeInput,
                    ),
                )
                and "class" not in field.widget.attrs
            ):
                current_classes = field.widget.attrs.get("class", "").split()
                if "form-control" not in current_classes:
                    current_classes.append("form-control")
                field.widget.attrs["class"] = " ".join(current_classes)

        if self.instance and self.instance.pk:
            if self.instance.sales_profile:
                self.fields["selected_profile_id"].initial = (
                    self.instance.sales_profile.pk
                )
            if getattr(self.instance, "motorcycle", None):
                self.fields["selected_motorcycle_id"].initial = (
                    self.instance.motorcycle.pk
                )

    def clean(self):
        cleaned_data = super().clean()
        self._warnings = []

        selected_profile_id = cleaned_data.get("selected_profile_id")
        selected_motorcycle_id = cleaned_data.get("selected_motorcycle_id")

        sales_profile = None
        motorcycle = None

        if selected_profile_id:
            try:
                sales_profile = SalesProfile.objects.get(pk=selected_profile_id)
                cleaned_data["sales_profile"] = sales_profile
            except SalesProfile.DoesNotExist:
                self.add_error(
                    "selected_profile_id", _("Selected sales profile does not exist.")
                )
        else:
            self.add_error(
                "selected_profile_id", _("A sales profile must be selected.")
            )

        if selected_motorcycle_id:
            try:
                motorcycle = Motorcycle.objects.get(pk=selected_motorcycle_id)
                cleaned_data["motorcycle"] = motorcycle
            except Motorcycle.DoesNotExist:
                self.add_error(
                    "selected_motorcycle_id", _("Selected motorcycle does not exist.")
                )
        else:
            self.add_error(
                "selected_motorcycle_id", _("A motorcycle must be selected.")
            )

        if self.errors:
            return cleaned_data

        appointment_date = cleaned_data.get("appointment_date")
        appointment_time = cleaned_data.get("appointment_time")
        booking_status = cleaned_data.get("booking_status")
        payment_status = cleaned_data.get("payment_status")
        amount_paid = cleaned_data.get("amount_paid")
        inventory_settings = InventorySettings.objects.first()

        if appointment_date and appointment_date < date.today():
            self._warnings.append(_("Warning: Appointment date is in the past."))

        if (
            appointment_date == date.today()
            and appointment_time
            and appointment_time < timezone.localtime(timezone.now()).time()
        ):
            self._warnings.append(
                _("Warning: Appointment time for today is in the past.")
            )

        if (
            booking_status == "confirmed"
            and inventory_settings
            and inventory_settings.deposit_amount > Decimal("0.00")
        ):
            if payment_status not in ["deposit_paid", "paid"]:
                self._warnings.append(
                    _(
                        "Warning: Booking is 'Confirmed' but no deposit or full payment recorded. Please verify payment status."
                    )
                )
            elif amount_paid < inventory_settings.deposit_amount:
                self._warnings.append(
                    _(
                        f"Warning: Booking is 'Confirmed' but recorded amount paid (${amount_paid}) is less than the required deposit (${inventory_settings.deposit_amount})."
                    )
                )

        if motorcycle and (
            booking_status == "confirmed" or booking_status == "reserved"
        ):
            should_warn_about_motorcycle_status = False
            warning_message_text = ""
            instance_motorcycle = getattr(self.instance, "motorcycle", None)

            if motorcycle.condition == "new":
                if motorcycle.quantity <= 0:
                    should_warn_about_motorcycle_status = True
                    warning_message_text = _(
                        f"Warning: The selected new motorcycle '{motorcycle.title}' is currently out of stock (quantity 0)."
                    )
                elif motorcycle.quantity == 1:
                    if (
                        _(
                            f"Warning: The selected new motorcycle '{motorcycle.title}' has only 1 unit remaining. Confirming this booking will make it out of stock."
                        )
                        not in self._warnings
                    ):
                        self._warnings.append(
                            _(
                                f"Warning: The selected new motorcycle '{motorcycle.title}' has only 1 unit remaining. Confirming this booking will make it out of stock."
                            )
                        )
                if motorcycle.status in ["reserved", "sold"]:
                    if not (
                        instance_motorcycle and instance_motorcycle.pk == motorcycle.pk
                    ):
                        should_warn_about_motorcycle_status = True
                        warning_message_text = _(
                            f"Warning: The selected new motorcycle '{motorcycle.title}' is currently '{motorcycle.get_status_display()}' (e.g., Reserved/Sold). Confirm this is acceptable."
                        )

            else:
                if motorcycle.status in ["reserved", "sold"]:
                    if not (
                        instance_motorcycle and instance_motorcycle.pk == motorcycle.pk
                    ):
                        should_warn_about_motorcycle_status = True
                        warning_message_text = _(
                            f"Warning: The selected motorcycle '{motorcycle.title}' is currently '{motorcycle.get_status_display()}'. Confirm this is acceptable."
                        )

            if (
                should_warn_about_motorcycle_status
                and warning_message_text
                and warning_message_text not in self._warnings
            ):
                self._warnings.append(warning_message_text)

        return cleaned_data

    def get_warnings(self):
        return getattr(self, "_warnings", [])
