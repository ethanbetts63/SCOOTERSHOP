from django import forms
from django.core.exceptions import ValidationError
from refunds.models.RefundRequest import RefundRequest
from service.models import ServiceBooking
from inventory.models import SalesBooking
from decimal import Decimal


class AdminRefundRequestForm(forms.ModelForm):
    # Service booking remains a dropdown as it's simpler.
    service_booking = forms.ModelChoiceField(
        queryset=ServiceBooking.objects.filter(
            payment_status__in=["paid", "deposit_paid", "refunded"]
        ).order_by("-created_at"),
        label="Select Service Booking",
        help_text="Choose a Service Booking (Paid, Deposit Paid, or Refunded status).",
        required=False,
    )

    # Sales booking is now an IntegerField with a hidden widget.
    # The template's JavaScript will populate this hidden field with the selected booking's ID.
    sales_booking = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
    )

    status = forms.ChoiceField(
        choices=RefundRequest.STATUS_CHOICES,
        label="Refund Status",
        help_text="Set the current status of the refund request.",
        required=False,
    )

    class Meta:
        model = RefundRequest
        # Note: 'sales_booking' is still here so Django knows to process it.
        fields = [
            "service_booking",
            "sales_booking",
            "reason",
            "staff_notes",
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
            "staff_notes": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Internal notes regarding the refund processing.",
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
        self.fields["staff_notes"].required = False
        self.fields["amount_to_refund"].required = True

        # If we are editing an existing instance, we need to populate the initial value
        # for our hidden sales_booking field.
        if self.instance and self.instance.pk and self.instance.sales_booking:
            self.initial['sales_booking'] = self.instance.sales_booking.pk

    def clean(self):
        cleaned_data = super().clean()
        service_booking = cleaned_data.get("service_booking")
        sales_booking_id = cleaned_data.get("sales_booking")
        amount_to_refund = cleaned_data.get("amount_to_refund")

        # Convert sales_booking_id to a model instance
        sales_booking = None
        if sales_booking_id:
            try:
                sales_booking = SalesBooking.objects.get(pk=sales_booking_id)
            except SalesBooking.DoesNotExist:
                self.add_error("sales_booking", "Invalid Sales Booking selected.")
        
        # Validation logic
        selected_bookings = [b for b in [service_booking, sales_booking] if b is not None]
        if len(selected_bookings) > 1:
            raise ValidationError("Please select only one type of booking (Service or Sales).")
        if not selected_bookings:
            raise ValidationError("Please select a Service or Sales Booking.")

        selected_booking = selected_bookings[0]
        max_refund_amount = Decimal("0.00")

        # Prepare instance for saving
        self.instance.service_booking = None
        self.instance.service_profile = None
        self.instance.sales_booking = None
        self.instance.sales_profile = None
        self.instance.payment = None

        if service_booking:
            if not service_booking.payment:
                self.add_error("service_booking", "Selected Service Booking does not have an associated payment record.")
                return cleaned_data
            self.instance.payment = service_booking.payment
            self.instance.service_booking = service_booking
            self.instance.service_profile = service_booking.service_profile
            max_refund_amount = service_booking.payment.amount

        elif sales_booking:
            if not sales_booking.payment:
                self.add_error("sales_booking", "Selected Sales Booking does not have an associated payment record.")
                return cleaned_data
            self.instance.payment = sales_booking.payment
            self.instance.sales_booking = sales_booking
            self.instance.sales_profile = sales_booking.sales_profile
            max_refund_amount = sales_booking.payment.amount

        if selected_booking and amount_to_refund is not None:
            if amount_to_refund < 0:
                self.add_error("amount_to_refund", "Amount to refund cannot be a negative value.")
            elif amount_to_refund > max_refund_amount:
                self.add_error(
                    "amount_to_refund",
                    f"Amount to refund (${amount_to_refund}) cannot exceed the amount paid for this booking (${max_refund_amount}).",
                )

        return cleaned_data

    def save(self, commit=True):
        # The clean method has already correctly assigned the sales_booking instance
        # to self.instance.sales_booking, so super().save() will work correctly.
        refund_request = super().save(commit=False)
        if commit:
            refund_request.save()
        return refund_request
