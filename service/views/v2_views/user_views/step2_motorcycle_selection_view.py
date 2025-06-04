from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

class Step2MotorcycleSelectionView(View):
    """
    Renders the second step of the booking process: Motorcycle Selection.
    Users select an existing motorcycle or choose to add a new one.
    """
    template_name = 'service/step2_motorcycle_selection.html'

    def get(self, request, *args, **kwargs):
        """Handles GET requests for Step 2."""
        context = {}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests for Step 2.
        Will eventually process MotorcycleSelectionForm submission.
        """
        messages.success(request, "Step 2 data processed (simulated).")
        return redirect('service:book_step3')

