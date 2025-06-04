from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

class Step3CustomerMotorcycleView(View):
    """
    Renders the third step of the booking process: Customer Motorcycle Details.
    Users provide details for a new or existing motorcycle.
    """
    template_name = 'service/step3_customer_motorcycle.html'

    def get(self, request, *args, **kwargs):
        """Handles GET requests for Step 3."""
        context = {}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests for Step 3.
        Will eventually process CustomerMotorcycleForm submission.
        """
        messages.success(request, "Step 3 data processed (simulated).")
        return redirect('service:book_step4')
