from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

class Step1ServiceDetailsView(View):
    """
    Renders the first step of the booking process: Service Details.
    Users select service type, drop-off date, and time.
    """
    template_name = 'service/step1_service_details.html'

    def get(self, request, *args, **kwargs):
        """Handles GET requests for Step 1."""
        context = {}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests for Step 1.
        Will eventually process ServiceDetailsForm submission.
        """
        messages.success(request, "Step 1 data processed (simulated).")
        return redirect('service:book_step2')
