from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

class Step7ConfirmationView(View):
    """
    Renders the final step of the booking process: Confirmation.
    Displays booking confirmation details to the user.
    """
    template_name = 'service/step7_confirmation.html'

    def get(self, request, *args, **kwargs):
        """Handles GET requests for Step 7."""
        context = {}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests for Step 7.
        Typically, this page is read-only, but a POST might be for a "Print" or "Download" action.
        """
        messages.info(request, "POST request received on confirmation page.")
        context = {}
        return render(request, self.template_name, context)
