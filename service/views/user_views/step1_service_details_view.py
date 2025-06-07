import uuid
import datetime
from django.shortcuts import redirect
from django.views import View
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from service.forms import ServiceDetailsForm
from service.models import TempServiceBooking, ServiceProfile, ServiceType, ServiceSettings, BlockedServiceDate
from service.models import CustomerMotorcycle

class Step1ServiceDetailsView(View):
    template_name = 'service/step1_service_details_include.html'

    def post(self, request, *args, **kwargs):
        # Remove any existing service booking reference from the session to start clean
        if 'service_booking_reference' in request.session:
            del request.session['service_booking_reference']
        
        form = ServiceDetailsForm(request.POST)
        service_settings = ServiceSettings.objects.first()
        
        errors_exist = False

        if form.is_valid():
            service_type = form.cleaned_data['service_type']
            service_date = form.cleaned_data['service_date']

            # Get current time in Perth timezone for advance notice calculations
            now_in_perth = timezone.localtime(timezone.now())
            
            # Check if service bookings are enabled
            if service_settings and not service_settings.enable_service_booking:
                messages.error(request, "Service bookings are currently disabled.")
                errors_exist = True

            # Check if anonymous bookings are allowed if user is not authenticated
            if service_settings and not service_settings.allow_anonymous_bookings and not request.user.is_authenticated:
                messages.error(request, "Anonymous bookings are not allowed. Please log in to book a service.")
                errors_exist = True
            
            # Enforce minimum advance notice for bookings
            if service_settings and service_settings.booking_advance_notice is not None:
                min_allowed_service_date = (now_in_perth + datetime.timedelta(days=service_settings.booking_advance_notice)).date()
                
                if service_date < min_allowed_service_date:
                    messages.error(request, f"Service date must be at least {service_settings.booking_advance_notice} days from now. Please choose a later date.")
                    errors_exist = True

            # Check if the selected date is an open day for bookings
            if service_settings and service_settings.booking_open_days:
                day_names = {
                    0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday',
                    4: 'Friday', 5: 'Saturday', 6: 'Sunday'
                }
                selected_day_of_week_full = day_names.get(service_date.weekday())
                open_days_list = [d.strip() for d in service_settings.booking_open_days.split(',')]

                abbreviated_day_names = {
                    0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu',
                    4: 'Fri', 5: 'Sat', 6: 'Sun'
                }
                selected_day_of_week_abbr = abbreviated_day_names.get(service_date.weekday())

                if selected_day_of_week_abbr not in open_days_list:
                    messages.error(request, f"Services are not available on {selected_day_of_week_full}s.")
                    errors_exist = True
            
            # Check for blocked service dates
            blocked_dates_overlap = BlockedServiceDate.objects.filter(
                start_date__lte=service_date,
                end_date__gte=service_date
            ).exists()
            if blocked_dates_overlap:
                messages.error(request, "Selected service date overlaps with a blocked service period.")
                errors_exist = True
            
            # If any validation errors exist, redirect
            if errors_exist:
                return redirect('core:index')

            temp_booking = None
            # Retrieve existing temporary booking UUID from session, using the consistent key
            temp_booking_uuid_from_session = request.session.get('temp_service_booking_uuid')

            if temp_booking_uuid_from_session:
                try:
                    # Attempt to get the existing TempServiceBooking object
                    temp_booking = TempServiceBooking.objects.get(session_uuid=temp_booking_uuid_from_session)
                except TempServiceBooking.DoesNotExist:
                    # If not found, set to None to create a new one
                    temp_booking = None

            service_profile_for_temp_booking = None
            customer_motorcycles_exist = False
            if request.user.is_authenticated:
                try:
                    # Get or create the service profile for the authenticated user
                    service_profile_for_temp_booking = request.user.service_profile
                    # Check if the user has any registered motorcycles
                    if service_profile_for_temp_booking.customer_motorcycles.exists():
                        customer_motorcycles_exist = True
                except ServiceProfile.DoesNotExist:
                    pass # User might not have a ServiceProfile yet, which is fine

            try:
                if temp_booking:
                    # Update existing temporary booking
                    temp_booking.service_type = service_type
                    temp_booking.service_date = service_date
                    if service_profile_for_temp_booking:
                        temp_booking.service_profile = service_profile_for_temp_booking
                    else:
                        temp_booking.service_profile = None # Ensure it's explicitly set to None if no profile
                    temp_booking.save()
                    messages.success(request, "Service details updated. Please choose your motorcycle.")
                else:
                    # Create a new temporary booking
                    temp_booking = TempServiceBooking.objects.create(
                        session_uuid=uuid.uuid4(),
                        service_type=service_type,
                        service_date=service_date,
                        service_profile=service_profile_for_temp_booking
                    )
                    # Store the new temporary booking UUID in the session using the consistent key
                    request.session['temp_service_booking_uuid'] = str(temp_booking.session_uuid)
                    messages.success(request, "Service details selected. Please choose your motorcycle.")

                # Determine the next redirect URL based on user authentication and existing motorcycles
                if request.user.is_authenticated and customer_motorcycles_exist:
                    # If authenticated and has motorcycles, go to step 2 (select motorcycle)
                    redirect_url = reverse('service:service_book_step2') + f'?temp_booking_uuid={temp_booking.session_uuid}'
                else:
                    # If not authenticated or no motorcycles, go to step 3 (add motorcycle)
                    redirect_url = reverse('service:service_book_step3') + f'?temp_booking_uuid={temp_booking.session_uuid}'
                
                return redirect(redirect_url)

            except Exception as e:
                # Catch any unexpected errors during saving
                messages.error(request, f"An unexpected error occurred while saving your selection: {e}")
                return redirect('core:index')

        else:
            # If the form is invalid, display errors to the user
            for field, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, f"Error in {field}: {error}")
            return redirect('core:index')

