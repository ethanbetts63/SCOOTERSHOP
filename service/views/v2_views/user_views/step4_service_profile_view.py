from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

class Step4ServiceProfileView(View):
    """
    Renders the fourth step of the booking process: Personal Information.
    Users provide or confirm their personal contact details.
    """
    template_name = 'service/step4_service_profile.html'

    def get(self, request, *args, **kwargs):
        """Handles GET requests for Step 4."""
        context = {}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests for Step 4.
        Will eventually process ServiceBookingUserForm submission.
        """
        messages.success(request, "Step 4 data processed (simulated).")
        return redirect('service:book_step5')
