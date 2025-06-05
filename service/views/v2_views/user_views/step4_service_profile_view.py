from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django.contrib import messages
from service.models import TempServiceBooking, ServiceProfile
from service.forms.step4_service_profile_form import ServiceBookingUserForm

class Step4ServiceProfileView(View):
    template_name = 'service/step4_service_profile.html' 
    form_class = ServiceBookingUserForm

    def _get_temp_booking(self, request):
        """
        Retrieves the TempServiceBooking instance from the session or redirects.
        """
        temp_booking_uuid = request.session.get('temp_booking_uuid')
        if not temp_booking_uuid:
            messages.error(request, "Your booking session has expired or is invalid. Please start over.")
            return None, redirect(reverse('service:service'))

        try:
            temp_booking = TempServiceBooking.objects.select_related(
                'customer_motorcycle', 
                'service_profile' # Pre-fetch related objects
            ).get(session_uuid=temp_booking_uuid)
            return temp_booking, None
        except TempServiceBooking.DoesNotExist:
            request.session.pop('temp_booking_uuid', None) # Clean up invalid session data
            messages.error(request, "Your booking session could not be found. Please start over.")
            return None, redirect(reverse('service:service')) # Or 'service:service'

    def _get_service_profile_instance(self, request, temp_booking):
        """
        Determines the ServiceProfile instance to use for the form.
        It prioritizes an existing profile on temp_booking, then user's profile, then None.
        """
        # 1. Check if a service_profile is already linked to the temp_booking
        if temp_booking and temp_booking.service_profile:
            return temp_booking.service_profile
        
        # 2. If user is authenticated, try to get their existing service_profile
        if request.user.is_authenticated:
            try:
                # Assuming ServiceProfile has a OneToOneField to User named 'user'
                # and related_name is 'service_profile'
                return request.user.service_profile
            except ServiceProfile.DoesNotExist:
                return None # Authenticated user, but no profile yet
            except AttributeError: # In case request.user doesn't have service_profile directly
                # This might happen if related_name isn't set or is different
                # Or if the OneToOneField is on User model instead of ServiceProfile
                # For now, we assume ServiceProfile.user is the link
                # If User.service_profile is the way, adjust access.
                # For safety, falling back to None if direct access fails.
                # It's better to ensure ServiceProfile.user is correctly set up.
                profile = ServiceProfile.objects.filter(user=request.user).first()
                return profile

        # 3. For anonymous users or authenticated users without a profile
        return None

    def dispatch(self, request, *args, **kwargs):
        """
        Handles initial request processing, retrieves temp_booking.
        """
        self.temp_booking, redirect_response = self._get_temp_booking(request)
        if redirect_response:
            return redirect_response
        
        # Ensure a motorcycle has been selected/added in a previous step
        if not self.temp_booking.customer_motorcycle:
            messages.warning(request, "Please select or add your motorcycle details first (Step 3).")
            return redirect(reverse('service:service_book_step3'))

        # self.service_settings = ServiceSettings.objects.first() # Uncomment if needed
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests: displays the form for customer details.
        """
        profile_instance = self._get_service_profile_instance(request, self.temp_booking)
        form = self.form_class(instance=profile_instance)
        
        context = {
            'form': form,
            'temp_booking': self.temp_booking,
            'step': 4, # Current step number
            'total_steps': 7, # Assuming 7 total steps, adjust if different
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests: processes submitted customer details.
        """
        profile_instance = self._get_service_profile_instance(request, self.temp_booking)
        form = self.form_class(request.POST, instance=profile_instance)

        if form.is_valid():
            service_profile = form.save(commit=False)

            # If user is authenticated and this is a new profile, link it to the user
            if request.user.is_authenticated and not service_profile.user_id: # Check user_id to ensure it's not already linked
                service_profile.user = request.user
            
            service_profile.save() # Save the new or updated ServiceProfile

            # Update TempServiceBooking with this ServiceProfile
            self.temp_booking.service_profile = service_profile
            
            # CRUCIAL: Link the CustomerMotorcycle (from TempServiceBooking) to this ServiceProfile
            # This ensures the motorcycle recorded in Step 3 is correctly associated with the customer profile from this step.
            if self.temp_booking.customer_motorcycle:
                motorcycle = self.temp_booking.customer_motorcycle
                if motorcycle.service_profile != service_profile: # Only update if different or not set
                    motorcycle.service_profile = service_profile
                    motorcycle.save(update_fields=['service_profile'])
            
            self.temp_booking.save(update_fields=['service_profile']) # Save changes to temp_booking

            messages.success(request, "Your details have been saved successfully.")
            return redirect(reverse('service:service_book_step5')) # Redirect to the next step
        else:
            # Form is invalid, re-render with errors
            messages.error(request, "Please correct the errors below.")
            context = {
                'form': form,
                'temp_booking': self.temp_booking,
                'step': 4,
                'total_steps': 7, 
            }
            return render(request, self.template_name, context)

