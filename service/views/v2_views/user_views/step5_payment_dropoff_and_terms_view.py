from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta

# Assuming the form is in 'service.forms.step5_payment_choice_and_terms_form'
# Ensure your project structure matches this import path.
from service.forms.step5_payment_choice_and_terms_form import PaymentOptionForm
from service.models import TempServiceBooking, ServiceSettings

class Step5PaymentDropoffAndTermsView(View):
    """
    Handles Step 5 of the service booking process: selecting drop-off details,
    choosing a payment method, and agreeing to terms.
    """
    template_name = 'service/step5_payment_dropoff_and_terms.html'
    form_class = PaymentOptionForm

    def _get_temp_booking(self, request):
        """
        Retrieves the TempServiceBooking instance from the session. If not found,
        it redirects the user to the starting page with an error message.
        """
        temp_booking_uuid = request.session.get('temp_booking_uuid')
        if not temp_booking_uuid:
            messages.error(request, "Your booking session has expired. Please start over.")
            return None, redirect(reverse('service:service')) # Adjust 'service:service' to your initial booking page URL
        
        try:
            # Eagerly load related objects to prevent extra database queries
            temp_booking = TempServiceBooking.objects.select_related(
                'service_type', 'customer_motorcycle', 'service_profile'
            ).get(session_uuid=temp_booking_uuid)
            return temp_booking, None
        except TempServiceBooking.DoesNotExist:
            request.session.pop('temp_booking_uuid', None) # Clean up invalid session data
            messages.error(request, "Your booking session could not be found. Please start over.")
            return None, redirect(reverse('service:service'))

    def dispatch(self, request, *args, **kwargs):
        """
        Central entry point for the view. Retrieves the temporary booking and service
        settings, and ensures previous steps have been completed before proceeding.
        """
        self.temp_booking, redirect_response = self._get_temp_booking(request)
        if redirect_response:
            return redirect_response

        # Prerequisite check: Ensure user has completed Step 4 (service profile)
        if not self.temp_booking.service_profile:
            messages.warning(request, "Please complete your personal details first (Step 4).")
            return redirect(reverse('service:service_book_step4')) # Correct URL name from urls.py

        # Fetch the singleton ServiceSettings
        self.service_settings = ServiceSettings.objects.first()
        if not self.service_settings:
            messages.error(request, "Service settings are not configured. Please contact an administrator.")
            return redirect(reverse('service:service'))

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """
        Prepares keyword arguments required for instantiating the form.
        The PaymentOptionForm requires both 'service_settings' and 'temp_booking'.
        """
        # Pass request to the form if it's needed for context (e.g., for user info)
        kwargs = {
            'service_settings': self.service_settings,
            'temp_booking': self.temp_booking,
        }
        return kwargs

    def get_context_data(self, **kwargs):
        """
        Prepares the context for rendering the template, including dynamic
        date constraints for the date picker.
        """
        today = timezone.localdate(timezone.now())
        service_date = self.temp_booking.service_date
        max_advance_days = self.service_settings.max_advance_dropoff_days
        
        # Drop-off date cannot be after the scheduled service date
        max_dropoff_date = service_date
        
        # Calculate the earliest possible drop-off date
        min_dropoff_date = service_date - timedelta(days=max_advance_days)

        # The earliest date cannot be in the past
        if min_dropoff_date < today:
            min_dropoff_date = today

        context = {
            'temp_booking': self.temp_booking,
            'service_settings': self.service_settings,
            'min_dropoff_date': min_dropoff_date.strftime('%Y-%m-%d'),
            'max_dropoff_date': max_dropoff_date.strftime('%Y-%m-%d'),
            'get_times_url': reverse('service:get_available_times_for_date'), # CORRECTED URL name
            'step': 5,
            'total_steps': 7,
        }
        context.update(kwargs)
        return context

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests. Initializes the form with any existing data from the
        temporary booking and renders the template.
        """
        initial_data = {
            'dropoff_date': self.temp_booking.dropoff_date,
            'dropoff_time': self.temp_booking.dropoff_time,
            'payment_option': self.temp_booking.payment_option,
        }
        form = self.form_class(initial=initial_data, **self.get_form_kwargs())
        
        context = self.get_context_data(form=form)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests. Validates the submitted form data. If valid,
        updates the TempServiceBooking instance and redirects to the next step.
        If invalid, re-renders the form with error messages.
        """
        form = self.form_class(request.POST, **self.get_form_kwargs())

        if form.is_valid():
            self.temp_booking.dropoff_date = form.cleaned_data['dropoff_date']
            self.temp_booking.dropoff_time = form.cleaned_data['dropoff_time']
            self.temp_booking.payment_option = form.cleaned_data['payment_option']
            
            # The 'service_terms_accepted' field is for validation only and is not saved.
            
            self.temp_booking.save(update_fields=['dropoff_date', 'dropoff_time', 'payment_option'])

            messages.success(request, "Drop-off and payment details have been saved successfully.")
            # Redirect to the next step (e.g., a summary page)
            return redirect(reverse('service:service_book_step6')) # Correct URL name from urls.py

        else:
            # Form is invalid, display errors to the user
            messages.error(request, "Please correct the errors highlighted below.")
            context = self.get_context_data(form=form)
            return render(request, self.template_name, context)
