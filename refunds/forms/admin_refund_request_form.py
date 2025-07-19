from django import forms
from refunds.models.RefundRequest import RefundRequest
from service.models import ServiceBooking
from inventory.models import SalesBooking
import re

class AdminRefundRequestForm(forms.ModelForm):
    booking_reference = forms.CharField(
        max_length=50,
        label="Booking Reference",
        help_text="Enter the booking reference (e.g., SVC-XXXXX or SBK-XXXXX).",
    )

    status = forms.ChoiceField(
        choices=RefundRequest.STATUS_CHOICES,
        label="Refund Status",
        help_text="Set the current status of the refund request.",
        required=False,
    )

    class Meta:
        model = RefundRequest
        fields = [
            "booking_reference",
            "reason",
            "amount_to_refund",
            "status",
        ]
        widgets = {
            "reason": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Optional: Reason for refund request (e.g., customer cancellation, service issue).",
                }
            ),
        }
        labels = {
            "reason": "Customer/Admin Reason",
            "amount_to_refund": "Amount to Refund ($)",
        }
        help_texts = {
            "amount_to_refund": "Enter the amount to be refunded. This cannot exceed the amount paid for the booking.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["reason"].required = False
        self.fields["amount_to_refund"].required = True

        # If editing an existing instance, populate booking_reference
        if self.instance and self.instance.pk:
            if self.instance.service_booking:
                self.initial["booking_reference"] = self.instance.service_booking.service_booking_reference
            elif self.instance.sales_booking:
                self.initial["booking_reference"] = self.instance.sales_booking.sales_booking_reference

    def clean_booking_reference(self):
        booking_reference = self.cleaned_data.get("booking_reference")
        if not booking_reference:
            raise forms.ValidationError("Booking reference is required.")
        return booking_reference

    def clean(self):
        cleaned_data = super().clean()
        booking_reference = cleaned_data.get("booking_reference") # This will now be populated if clean_booking_reference passed
        amount_to_refund = cleaned_data.get("amount_to_refund")

        booking_object = None
        payment_object = None
        booking_type = None

        if booking_reference: # Only proceed if booking_reference is present
            # Try to find service booking
            if re.match(r"^(SERVICE|SVC)-\w+", booking_reference, re.IGNORECASE):
                try:
                    booking_object = ServiceBooking.objects.get(
                        service_booking_reference__iexact=booking_reference
                    )
                    payment_object = booking_object.payment
                    booking_type = "service"
                except ServiceBooking.DoesNotExist:
                    pass

            # If not found, try to find sales booking
            if not booking_object and re.match(r"^SBK-\w+", booking_reference, re.IGNORECASE):
                try:
                    booking_object = SalesBooking.objects.get(
                        sales_booking_reference__iexact=booking_reference
                    )
                    payment_object = booking_object.payment
                    booking_type = "sales"
                except SalesBooking.DoesNotExist:
                    pass

            if not booking_object:
                self.add_error(
                    "booking_reference",
                    "No booking found with this reference number.",
                )
            elif not payment_object:
                self.add_error(
                    "booking_reference",
                    "No payment record found for this booking.",
                )
            elif payment_object.status != "succeeded":
                self.add_error(
                    "booking_reference",
                    "This booking's payment is not in a 'succeeded' status and is not eligible for a refund.",
                )
            else:
                # Assign the found booking object to the instance
                self.instance.service_booking = None
                self.instance.sales_booking = None
                self.instance.payment = payment_object

                if booking_type == "service":
                    self.instance.service_booking = booking_object
                    self.instance.service_profile = booking_object.service_profile
                elif booking_type == "sales":
                    self.instance.sales_booking = booking_object
                    self.instance.sales_profile = booking_object.sales_profile

                max_refund_amount = payment_object.amount

                if amount_to_refund is not None:
                    if amount_to_refund < 0:
                        self.add_error(
                            "amount_to_refund", "Amount to refund cannot be a negative value."
                        )
                    elif amount_to_refund > max_refund_amount:
                        self.add_error(
                            "amount_to_refund",
                            f"Amount to refund (${amount_to_refund}) cannot exceed the amount paid for this booking (${max_refund_amount}).",
                        )
        # No else block here, as clean_booking_reference handles the required check

        return cleaned_data

    def save(self, commit=True):
        refund_request = super().save(commit=False)
        if commit:
            refund_request.save()
        return refund_request
