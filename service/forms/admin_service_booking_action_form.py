from service.models import ServiceBooking
from django import forms
from decimal import Decimal


class ServiceBookingActionForm(forms.Form):
    message = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Optional message to the customer (e.g., specific instructions, reasons for rejection, etc.)",
            }
        ),
        required=False,
        help_text="An optional message to include in the notification email.",
    )
    send_notification = forms.BooleanField(
        required=False,
        initial=True,
        label="Send notification email to customer",
        help_text="Check to send an email notification about this action to the customer.",
    )
    action = forms.CharField(
        widget=forms.HiddenInput(),
        required=True,
        help_text="Hidden field to specify whether the action is 'confirm' or 'reject'.",
    )
    service_booking_id = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=True,
        help_text="Hidden field for the Service Booking ID.",
    )

    estimated_pickup_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        required=True,
        help_text="Estimated pickup date for the service.",
    )
    estimated_pickup_time = forms.TimeField(
        widget=forms.TimeInput(attrs={"type": "time"}),
        required=True,
        help_text="Estimated pickup time for the service.",
    )

    initiate_refund = forms.BooleanField(
        required=False,
        label="Initiate Refund for Deposit",
        help_text="Check this box to initiate a refund for the deposit paid for this booking.",
    )
    refund_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Amount to Refund (AUD)",
        min_value=Decimal("0.01"),
        help_text="The amount to refund to the customer. Max is the amount paid for the booking.",
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get("action")
        initiate_refund = cleaned_data.get("initiate_refund")
        refund_amount = cleaned_data.get("refund_amount")
        service_booking_id = cleaned_data.get("service_booking_id")

        if action == "reject":
            if initiate_refund:
                if refund_amount is None:
                    self.add_error(
                        "refund_amount",
                        "Please enter a refund amount if initiating a refund.",
                    )
                elif refund_amount <= 0:
                    self.add_error(
                        "refund_amount", "Refund amount must be greater than zero."
                    )
                else:
                    try:
                        booking = ServiceBooking.objects.get(pk=service_booking_id)
                        if booking.payment and refund_amount > booking.payment.amount:
                            self.add_error(
                                "refund_amount",
                                f"Refund amount cannot exceed the amount paid ({booking.payment.amount:.2f} {booking.payment.currency}).",
                            )
                        elif not booking.payment or booking.payment.amount <= 0:
                            self.add_error(
                                "refund_amount",
                                "Cannot initiate refund: No valid payment found for this booking or amount paid is zero.",
                            )

                    except ServiceBooking.DoesNotExist:
                        self.add_error(None, "Service booking not found.")
            elif refund_amount is not None:
                self.add_error(
                    "initiate_refund",
                    "Please check 'Initiate Refund for Deposit' to specify a refund amount.",
                )

        return cleaned_data
