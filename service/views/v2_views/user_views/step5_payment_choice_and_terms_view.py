from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

class Step5PaymentChoiceAndTermsView(View):
    """
    Renders the fifth step of the booking process: Payment Option & Terms.
    Users select their preferred payment method and accept terms and conditions.
    """
    template_name = 'service/step5_payment_choice_and_terms.html'

    def get(self, request, *args, **kwargs):
        """Handles GET requests for Step 5."""
        context = {}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests for Step 5.
        Will eventually process PaymentOptionForm submission and redirect based on choice.
        """
        messages.success(request, "Step 5 data processed (simulated).")
        return redirect('service:book_step6')
