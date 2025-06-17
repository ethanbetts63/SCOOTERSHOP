# SCOOTER_SHOP/inventory/forms.py

from django import forms

class SalesBookingActionForm(forms.Form):
    """
    Form for processing sales booking approval or rejection actions.
    Includes an optional message and a checkbox for sending notifications.
    A hidden 'action' field will determine if it's a 'confirm' or 'reject' action.
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
    # Hidden field to specify the action (e.g., 'confirm', 'reject')
    # This value will be set by the JavaScript on the frontend when a button is clicked.
    action = forms.CharField(
        widget=forms.HiddenInput(),
        required=True,
        help_text="Hidden field to specify whether the action is 'confirm' or 'reject'."
    )
    # Hidden field for the sales booking ID
    sales_booking_id = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=True,
        help_text="Hidden field for the Sales Booking ID."
    )
