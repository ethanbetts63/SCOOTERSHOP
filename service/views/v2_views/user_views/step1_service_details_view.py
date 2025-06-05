import uuid
import datetime
from django.shortcuts import redirect
from django.views import View
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone # For making datetime objects timezone-aware
from django.conf import settings # To access TIME_ZONE from settings

from service.forms import ServiceDetailsForm
from service.models import TempServiceBooking, ServiceProfile, ServiceType, ServiceSettings, BlockedServiceDate
from service.models import CustomerMotorcycle

class Step1ServiceDetailsView(View):
    def post(self, request, *args, **kwargs):
        # Clear any existing service booking reference from the session
        if 'service_booking_reference' in request.session:
            del request.session['service_booking_reference']
        
        form = ServiceDetailsForm(request.POST)
        service_settings = ServiceSettings.objects.first()
        
        errors_exist = False

        if form.is_valid():
            # Retrieve cleaned data from the form
            service_type = form.cleaned_data['service_type']
            service_date = form.cleaned_data['service_date'] # Now using service_date directly

            # Get the current time in the project's default timezone (Australia/Perth)
            now_in_perth = timezone.localtime(timezone.now())
            
            # --- View-Level Validation Checks for Service Date ---

            # Rule: Globally enable or disable the service booking system.
            if service_settings and not service_settings.enable_service_booking:
                messages.error(request, "Service bookings are currently disabled.")
                errors_exist = True

            # Rule: Allow users to book without creating an account.
            if service_settings and not service_settings.allow_anonymous_bookings and not request.user.is_authenticated:
                messages.error(request, "Anonymous bookings are not allowed. Please log in to book a service.")
                errors_exist = True
            
            # Rule: Service date must be at least 'booking_advance_notice' days from now (Perth time).
            # This applies to the service date, not necessarily the drop-off date.
            if service_settings and service_settings.booking_advance_notice is not None:
                # Calculate the minimum allowed service date
                min_allowed_service_date = (now_in_perth + datetime.timedelta(days=service_settings.booking_advance_notice)).date()
                
                # Compare the user's selected service date against this minimum
                if service_date < min_allowed_service_date:
                    messages.error(request, f"Service date must be at least {service_settings.booking_advance_notice} days from now. Please choose a later date.")
                    errors_exist = True

            # Rule: Selected service date must fall on an open day (Mon, Tue, etc.) in Perth.
            if service_settings and service_settings.booking_open_days:
                day_names = {
                    0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday',
                    4: 'Friday', 5: 'Saturday', 6: 'Sunday'
                }
                # Use the full day name for the error message
                selected_day_of_week_full = day_names.get(service_date.weekday())
                open_days_list = [d.strip() for d in service_settings.booking_open_days.split(',')]

                # To be consistent with the test, and assuming `booking_open_days` stores abbreviations
                abbreviated_day_names = {
                    0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu',
                    4: 'Fri', 5: 'Sat', 6: 'Sun'
                }
                selected_day_of_week_abbr = abbreviated_day_names.get(service_date.weekday())

                if selected_day_of_week_abbr not in open_days_list:
                    # Use the full name for the user-facing error message
                    messages.error(request, f"Services are not available on {selected_day_of_week_full}s.")
                    errors_exist = True
            
            # Rule: Selected service date must not overlap with any blocked service period.
            blocked_dates_overlap = BlockedServiceDate.objects.filter(
                start_date__lte=service_date,
                end_date__gte=service_date
            ).exists()
            if blocked_dates_overlap:
                messages.error(request, "Selected service date overlaps with a blocked service period.")
                errors_exist = True
            
            # If any errors exist from the view-level validations, redirect.
            if errors_exist:
                return redirect('core:index')

            temp_booking = None
            temp_booking_uuid = request.session.get('temp_booking_uuid')

            # Attempt to retrieve an existing temporary booking if a UUID is present in the session
            if temp_booking_uuid:
                try:
                    temp_booking = TempServiceBooking.objects.get(session_uuid=temp_booking_uuid)
                except TempServiceBooking.DoesNotExist:
                    temp_booking = None # Reset if not found

            service_profile_for_temp_booking = None
            customer_motorcycles_exist = False
            # Check if the user is authenticated and has a service profile with motorcycles
            if request.user.is_authenticated:
                try:
                    service_profile_for_temp_booking = request.user.service_profile
                    if service_profile_for_temp_booking.customer_motorcycles.exists():
                        customer_motorcycles_exist = True
                except ServiceProfile.DoesNotExist:
                    pass 

            try:
                # Update existing temporary booking or create a new one
                if temp_booking:
                    temp_booking.service_type = service_type
                    temp_booking.service_date = service_date # Update service_date
                    # dropoff_date and dropoff_time will be set in a later step
                    if service_profile_for_temp_booking:
                        temp_booking.service_profile = service_profile_for_temp_booking
                    else:
                        temp_booking.service_profile = None # Explicitly set to None if no profile
                    temp_booking.save()
                    messages.success(request, "Service details updated. Please choose your motorcycle.")
                else:
                    # Create a new TempServiceBooking with service_type and service_date
                    temp_booking = TempServiceBooking.objects.create(
                        session_uuid=uuid.uuid4(),
                        service_type=service_type,
                        service_date=service_date, # Save service_date
                        # dropoff_date and dropoff_time are now nullable in the model
                        service_profile=service_profile_for_temp_booking
                    )
                    request.session['temp_booking_uuid'] = str(temp_booking.session_uuid)
                    messages.success(request, "Service details selected. Please choose your motorcycle.")

                # Conditional redirection logic based on user authentication and existing motorcycles
                if request.user.is_authenticated and customer_motorcycles_exist:
                    # Redirect to step 2 if authenticated and has motorcycles
                    # Corrected URL name: service_book_step2
                    redirect_url = reverse('service:service_book_step2') + f'?temp_booking_uuid={temp_booking.session_uuid}'
                else:
                    # Redirect to step 3 if not authenticated or no motorcycles
                    # Corrected URL name: service_book_step3
                    redirect_url = reverse('service:service_book_step3') + f'?temp_booking_uuid={temp_booking.session_uuid}'
                
                return redirect(redirect_url)

            except Exception as e:
                # Handle unexpected errors during saving
                messages.error(request, f"An unexpected error occurred while saving your selection: {e}")
                return redirect('core:index')

        else:
            # If the form is not valid, display form errors
            for field, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, f"Error in {field}: {error}")
            return redirect('core:index')

