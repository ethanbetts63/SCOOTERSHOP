from django.shortcuts import render
from django.views import View

class UserConfirmationRefundRequestView(View):
    """
    Displays a confirmation page after a user successfully submits a refund request.
    Informs the user to check their email for a verification link.
    """
    template_name = 'payments/user_confirmation_refund_request.html'

    def get(self, request, *args, **kwargs):
        """
        Renders the confirmation page.
        """
        context = {
            'page_title': 'Refund Request Submitted',
            'message': 'Your refund request has been submitted successfully. A confirmation email has been sent to your inbox. Please click the link in the email to confirm your refund request.',
            'additional_info': 'If you do not receive an email within a few minutes, please check your spam folder.',
        }
        return render(request, self.template_name, context)
