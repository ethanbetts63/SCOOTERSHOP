from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from service.forms import MotorcycleSelectionForm, ADD_NEW_MOTORCYCLE_OPTION
from service.models import TempServiceBooking, CustomerMotorcycle, ServiceProfile

class Step2MotorcycleSelectionView(LoginRequiredMixin, View):
    template_name = 'service/step2_motorcycle_selection.html'

    def dispatch(self, request, *args, **kwargs):
        # Retrieve the temporary booking UUID from the session using the consistent key
        session_uuid = request.session.get('temp_service_booking_uuid')

        # If no temporary booking UUID is found, redirect to the service home page
        if not session_uuid:
            return redirect(reverse('service:service'))

        try:
            # Attempt to retrieve the TempServiceBooking object based on the session UUID
            self.temp_booking = TempServiceBooking.objects.get(session_uuid=session_uuid)
        except TempServiceBooking.DoesNotExist:
            # If the temporary booking does not exist, remove the UUID from the session and redirect
            request.session.pop('temp_service_booking_uuid', None)
            return redirect(reverse('service:service'))

        # If the temporary booking does not have an associated service profile, redirect to step 3
        if not self.temp_booking.service_profile:
            return redirect(reverse('service:service_book_step3'))

        # Set the service profile for easier access within the view
        self.service_profile = self.temp_booking.service_profile

        # Check if the service profile has any associated customer motorcycles
        has_motorcycles = self.service_profile.customer_motorcycles.exists()

        # If no motorcycles exist for the profile, redirect to step 3 (add motorcycle)
        if not has_motorcycles:
            return redirect(reverse('service:service_book_step3'))
        
        # Continue with the normal dispatch process if all checks pass
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Initialize the motorcycle selection form with the current service profile
        form = MotorcycleSelectionForm(service_profile=self.service_profile)
        context = {
            'form': form,
            'temp_booking': self.temp_booking,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        # Process the submitted form data
        form = MotorcycleSelectionForm(service_profile=self.service_profile, data=request.POST)

        if form.is_valid():
            selected_motorcycle_value = form.cleaned_data['selected_motorcycle']

            # Check if the user opted to add a new motorcycle
            if selected_motorcycle_value == ADD_NEW_MOTORCYCLE_OPTION:
                # Redirect to step 3 to add a new motorcycle
                return redirect(reverse('service:service_book_step3'))
            else:
                try:
                    # Attempt to convert the selected motorcycle value to an integer ID
                    motorcycle_id = int(selected_motorcycle_value)
                    # Retrieve the selected motorcycle from the database, ensuring it belongs to the current service profile
                    motorcycle = get_object_or_404(
                        CustomerMotorcycle,
                        pk=motorcycle_id,
                        service_profile=self.service_profile
                    )
                    # Associate the selected motorcycle with the temporary booking
                    self.temp_booking.customer_motorcycle = motorcycle
                    self.temp_booking.save()
                    # Redirect to the next step (step 4)
                    return redirect(reverse('service:service_book_step4'))
                except (ValueError, CustomerMotorcycle.DoesNotExist):
                    # If the motorcycle ID is invalid or the motorcycle does not exist, add an error to the form
                    form.add_error('selected_motorcycle', "Invalid motorcycle selection.")
        
        # If the form is invalid or an error occurred, re-render the form with errors
        context = {
            'form': form,
            'temp_booking': self.temp_booking,
        }
        return render(request, self.template_name, context)

