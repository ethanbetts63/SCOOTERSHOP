# service/views/user_views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from service.forms import MotorcycleSelectionForm, ADD_NEW_MOTORCYCLE_OPTION
from service.models import TempServiceBooking, CustomerMotorcycle, ServiceProfile

class Step2MotorcycleSelectionView(LoginRequiredMixin, View):
    """
    Step 2 of the service booking flow.
    Allows an authenticated user to select an existing motorcycle from their
    ServiceProfile or choose to add a new one.
    """
    template_name = 'service/step2_motorcycle_selection.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Ensures a TempServiceBooking instance exists in the session and is linked
        to an authenticated user's ServiceProfile before proceeding.
        Handles redirection if prerequisites are not met or if the user
        should skip this step (e.g., no existing motorcycles).
        """
        session_uuid = request.session.get('temp_booking_uuid')

        # If no temporary booking UUID in session, redirect to the start of the service flow
        if not session_uuid:
            return redirect(reverse('service:service'))

        try:
            self.temp_booking = TempServiceBooking.objects.get(session_uuid=session_uuid)
        except TempServiceBooking.DoesNotExist:
            request.session.pop('temp_booking_uuid', None)
            return redirect(reverse('service:service'))

        if not self.temp_booking.service_profile:
            return redirect(reverse('service:service_book_step3'))


        self.service_profile = self.temp_booking.service_profile

        has_motorcycles = self.service_profile.customer_motorcycles.exists()

        # If the user has no existing motorcycles, redirect them to Step 3 to add one.
        if not has_motorcycles:
            return redirect(reverse('service:service_book_step3'))

        # If all checks pass and the user has motorcycles, proceed with the view
        
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests, displaying the MotorcycleSelectionForm.
        """
        # Pass the service_profile to the form to populate motorcycle choices
        form = MotorcycleSelectionForm(service_profile=self.service_profile)
        context = {
            'form': form,
            'temp_booking': self.temp_booking,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, processing the selected motorcycle or 'add new' option.
        """
        # The form needs the service_profile to filter the motorcycles
        form = MotorcycleSelectionForm(service_profile=self.service_profile, data=request.POST)

        if form.is_valid():
            selected_motorcycle_value = form.cleaned_data['selected_motorcycle']

            if selected_motorcycle_value == ADD_NEW_MOTORCYCLE_OPTION:
                # User chose to add a new motorcycle, redirect to Step 3
                return redirect(reverse('service:service_book_step3'))
            else:
                # User selected an existing motorcycle
                try:
                    motorcycle_id = int(selected_motorcycle_value)
                    # Fetch the motorcycle, ensuring it belongs to the current user's profile
                    motorcycle = get_object_or_404(
                        CustomerMotorcycle,
                        pk=motorcycle_id,
                        service_profile=self.service_profile # Ensure the motorcycle belongs to this profile
                    )
                    # Link the selected motorcycle to the temporary booking
                    self.temp_booking.customer_motorcycle = motorcycle
                    self.temp_booking.save()
                    # Redirect to the next step, which is Step 4 (Service Profile/Personal Info)
                    return redirect(reverse('service:service_book_step4'))
                except (ValueError, CustomerMotorcycle.DoesNotExist):
                    # Handle cases where the motorcycle ID is invalid or doesn't belong to the user
                    form.add_error('selected_motorcycle', "Invalid motorcycle selection.")
        
        # If form is not valid or an error occurred during motorcycle lookup, re-render with errors
        context = {
            'form': form,
            'temp_booking': self.temp_booking,
        }
        return render(request, self.template_name, context)

