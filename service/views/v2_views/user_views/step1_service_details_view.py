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
        if 'service_booking_reference' in request.session:
            del request.session['service_booking_reference']
        
        form = ServiceDetailsForm(request.POST)
        service_settings = ServiceSettings.objects.first()
        
        errors_exist = False

        if form.is_valid():
            service_type = form.cleaned_data['service_type']
            dropoff_date = form.cleaned_data['dropoff_date']
            dropoff_time = form.cleaned_data['dropoff_time']

            # Get the current time in the project's default timezone (Australia/Perth)
            now_in_perth = timezone.localtime(timezone.now())
            
            # Combine the user's selected date and time, and make it aware of the Perth timezone
            # This creates a timezone-aware datetime object for the drop-off in Perth time.
            dropoff_datetime_in_perth = timezone.make_aware(
                datetime.datetime.combine(dropoff_date, dropoff_time),
                timezone=timezone.pytz.timezone(settings.TIME_ZONE)
            )

            # --- View-Level Validation Checks ---

            # Rule: Globally enable or disable the service booking system.
            if service_settings and not service_settings.enable_service_booking:
                messages.error(request, "Service bookings are currently disabled.")
                errors_exist = True

            # Rule: Allow users to book without creating an account.
            if service_settings and not service_settings.allow_anonymous_bookings and not request.user.is_authenticated:
                messages.error(request, "Anonymous bookings are not allowed. Please log in to book a service.")
                errors_exist = True
            
            # Rule: Drop-off must be at least 'booking_advance_notice' days from now (Perth time).
            if service_settings and service_settings.booking_advance_notice is not None:
                # Calculate the minimum allowed drop-off datetime based on Perth's current time and advance notice
                min_allowed_dropoff_datetime_in_perth = now_in_perth + datetime.timedelta(days=service_settings.booking_advance_notice)
                
                # Compare the user's selected drop-off datetime against this minimum
                if dropoff_datetime_in_perth < min_allowed_dropoff_datetime_in_perth:
                    messages.error(request, f"Drop-off must be at least {service_settings.booking_advance_notice} days from now. Please choose a later date/time.")
                    errors_exist = True

            # Rule: Selected drop-off date must fall on an open day (Mon, Tue, etc.) in Perth.
            if service_settings and service_settings.booking_open_days:
                day_names = {
                    0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu',
                    4: 'Fri', 5: 'Sat', 6: 'Sun'
                }
                selected_day_of_week_abbr = day_names.get(dropoff_date.weekday())
                open_days_list = [d.strip() for d in service_settings.booking_open_days.split(',')]

                if selected_day_of_week_abbr not in open_days_list:
                    messages.error(request, f"Bookings are not open on {selected_day_of_week_abbr}s.")
                    errors_exist = True
            
            # Rule: Selected drop-off time must be within operational start and end times (Perth time).
            if service_settings:
                # dropoff_time is a datetime.time object, which is timezone-naive.
                # It's compared directly against ServiceSettings.drop_off_start_time and _end_time,
                # which are also naive time objects representing Perth's operational hours.
                if not (service_settings.drop_off_start_time <= dropoff_time <= service_settings.drop_off_end_time):
                    messages.error(request, f"Drop-off time must be between {service_settings.drop_off_start_time.strftime('%H:%M')} and {service_settings.drop_off_end_time.strftime('%H:%M')}.")
                    errors_exist = True

            # Rule: Selected date must not overlap with any blocked service period.
            blocked_dates_overlap = BlockedServiceDate.objects.filter(
                start_date__lte=dropoff_date,
                end_date__gte=dropoff_date
            ).exists()
            if blocked_dates_overlap:
                messages.error(request, "Selected date overlaps with a blocked service period.")
                errors_exist = True
            
            if errors_exist:
                return redirect('core:index')

            temp_booking = None
            temp_booking_uuid = request.session.get('temp_booking_uuid')

            if temp_booking_uuid:
                try:
                    temp_booking = TempServiceBooking.objects.get(session_uuid=temp_booking_uuid)
                except TempServiceBooking.DoesNotExist:
                    temp_booking = None

            service_profile_for_temp_booking = None
            customer_motorcycles_exist = False
            if request.user.is_authenticated:
                try:
                    service_profile_for_temp_booking = request.user.service_profile
                    if service_profile_for_temp_booking.customer_motorcycles.exists():
                        customer_motorcycles_exist = True
                except ServiceProfile.DoesNotExist:
                    pass

            try:
                if temp_booking:
                    temp_booking.service_type = service_type
                    temp_booking.dropoff_date = dropoff_date
                    temp_booking.dropoff_time = dropoff_time
                    if service_profile_for_temp_booking:
                        temp_booking.service_profile = service_profile_for_temp_booking
                    temp_booking.save()
                    messages.success(request, "Service details updated. Please choose your motorcycle.")
                else:
                    temp_booking = TempServiceBooking.objects.create(
                        session_uuid=uuid.uuid4(),
                        service_type=service_type,
                        dropoff_date=dropoff_date,
                        dropoff_time=dropoff_time,
                        service_profile=service_profile_for_temp_booking
                    )
                    request.session['temp_booking_uuid'] = str(temp_booking.session_uuid)
                    messages.success(request, "Service details selected. Please choose your motorcycle.")

                # Conditional redirection logic
                if request.user.is_authenticated and customer_motorcycles_exist:
                    redirect_url = reverse('service:step2_choose_motorcycle') + f'?temp_booking_uuid={temp_booking.session_uuid}'
                else:
                    redirect_url = reverse('service:step3_customer_motorcycle_details') + f'?temp_booking_uuid={temp_booking.session_uuid}'
                
                return redirect(redirect_url)

            except Exception as e:
                messages.error(request, f"An unexpected error occurred while saving your selection: {e}")
                return redirect('core:index')

        else:
            for field, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, f"Error in {field}: {error}")
            return redirect('core:index')
