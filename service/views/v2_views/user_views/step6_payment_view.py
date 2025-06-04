from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

class Step6PaymentView(View):
    """
    Renders the sixth step of the booking process: Payment.
    This page handles the actual payment processing.
    """
    template_name = 'service/step6_payment.html'

    def get(self, request, *args, **kwargs):
        """Handles GET requests for Step 6."""
        context = {}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests for Step 6.
        Will eventually process payment submission.
        """
        messages.success(request, "Step 6 payment processed (simulated).")
        return redirect('service:book_step7')

