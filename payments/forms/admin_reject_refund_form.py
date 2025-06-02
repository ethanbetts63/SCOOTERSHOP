# payments/forms/admin_reject_refund_form.py

from django import forms
from payments.models import HireRefundRequest

class AdminRejectRefundForm(forms.ModelForm):
    """
    Form for administrators to reject a HireRefundRequest,
    allowing them to provide a rejection reason and choose
    whether to send an automated email to the user.
    """
    # Add a boolean field for sending the email, not directly part of the model
    send_rejection_email = forms.BooleanField(
        label="Send automated rejection email to user",
        required=False, # Make it optional
        initial=True,   # Default to checked, as discussed
        help_text="If checked, an email containing the rejection reason will be sent to the user."
    )

    class Meta:
        model = HireRefundRequest
        # Only include the rejection_reason field from the model
        fields = ['rejection_reason']
        widgets = {
            'rejection_reason': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Enter reason for rejection...'}),
        }
        labels = {
            'rejection_reason': 'Reason for Rejection',
        }
        help_texts = {
            'rejection_reason': 'Provide a clear and concise reason for rejecting this refund request.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap/Tailwind-friendly classes to the rejection_reason field
        self.fields['rejection_reason'].widget.attrs.update({
            'class': 'form-control block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'
        })
        # Add Bootstrap/Tailwind-friendly classes to the send_rejection_email checkbox
        self.fields['send_rejection_email'].widget.attrs.update({
            'class': 'form-check-input h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'
        })
