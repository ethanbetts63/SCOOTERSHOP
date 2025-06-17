# SCOOTER_SHOP/inventory/forms.py
from inventory.models import SalesBooking
from django import forms
from decimal import Decimal # Import Decimal for default value

class SalesBookingActionForm(forms.Form):
    """
    Form for processing sales booking approval or rejection actions.
    Includes an optional message and a checkbox for sending notifications.
    Also includes fields for initiating a refund during rejection if applicable.
    """
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Optional message to the customer (e.g., specific instructions, reasons for rejection, etc.)'}),
        required=False,
        help_text="An optional message to include in the notification email."
    )
    send_notification = forms.BooleanField(
        required=False,
        initial=True,
        label="Send notification email to customer",
        help_text="Check to send an email notification about this action to the customer."
    )
    action = forms.CharField(
        widget=forms.HiddenInput(),
        required=True,
        help_text="Hidden field to specify whether the action is 'confirm' or 'reject'."
    )
    sales_booking_id = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=True,
        help_text="Hidden field for the Sales Booking ID."
    )

    # NEW: Refund-related fields
    initiate_refund = forms.BooleanField(
        required=False,
        label="Initiate Refund for Deposit",
        help_text="Check this box to initiate a refund for the deposit paid for this booking.",
        # This field will only be displayed and validated if action is 'reject' AND payment_status is 'deposit_paid'
    )
    refund_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Amount to Refund (AUD)", # Assuming AUD based on PaymentModel, adjust if needed
        min_value=Decimal('0.01'), # Minimum refund amount
        help_text="The amount to refund to the customer. Max is the amount paid for the booking.",
        # This field will only be displayed and validated if 'initiate_refund' is checked.
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        initiate_refund = cleaned_data.get('initiate_refund')
        refund_amount = cleaned_data.get('refund_amount')
        sales_booking_id = cleaned_data.get('sales_booking_id')

        # Only perform refund-specific validation if the action is 'reject'
        if action == 'reject':
            if initiate_refund:
                if refund_amount is None:
                    self.add_error('refund_amount', "Please enter a refund amount if initiating a refund.")
                elif refund_amount <= 0:
                    self.add_error('refund_amount', "Refund amount must be greater than zero.")
                else:
                    # Fetch the booking to get the original amount paid
                    try:
                        booking = SalesBooking.objects.get(pk=sales_booking_id)
                        if booking.payment and refund_amount > booking.payment.amount:
                            self.add_error('refund_amount', f"Refund amount cannot exceed the amount paid ({booking.payment.amount:.2f} {booking.payment.currency}).")
                        elif not booking.payment or booking.payment.amount <= 0:
                             self.add_error('refund_amount', "Cannot initiate refund: No valid payment found for this booking or amount paid is zero.")
                        
                    except SalesBooking.DoesNotExist:
                        # This should ideally be caught earlier by the view's dispatch,
                        # but good to have a fallback here.
                        self.add_error(None, "Sales booking not found.")
            elif refund_amount is not None:
                # If refund_amount is provided but initiate_refund is not checked
                self.add_error('initiate_refund', "Please check 'Initiate Refund for Deposit' to specify a refund amount.")

        return cleaned_data
