import datetime
import uuid
from django.shortcuts import redirect
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse # Import reverse for dynamic URL lookup

from ..forms.step1_DateTime_form import Step1DateTimeForm
from ..models import TempHireBooking, DriverProfile # Import DriverProfile
from dashboard.models import HireSettings, BlockedHireDate


class SelectDateTimeView(View):
    """
    Handles the submission of the Step 1 Date/Time/License form.
    This view is POST-only. It processes the form and redirects to Step 2.
    """

    def post(self, request, *args, **kwargs):
        form = Step1DateTimeForm(request.POST)
        hire_settings = HireSettings.objects.first()

        if form.is_valid():
            pickup_date = form.cleaned_data['pick_up_date']
            pickup_time = form.cleaned_data['pick_up_time']
            return_date = form.cleaned_data['return_date']
            return_time = form.cleaned_data['return_time']
            has_motorcycle_license = form.cleaned_data['has_motorcycle_license']

            pickup_datetime = timezone.make_aware(datetime.datetime.combine(pickup_date, pickup_time))
            return_datetime = timezone.make_aware(datetime.datetime.combine(return_date, return_time))
            now = timezone.now()

            # --- Validation Checks ---
            errors_exist = False

            if return_datetime <= pickup_datetime:
                messages.error(request, "Return date and time must be after pickup date and time.")
                errors_exist = True

            if hire_settings and hire_settings.minimum_hire_duration_days is not None:
                min_duration = datetime.timedelta(days=hire_settings.minimum_hire_duration_days)
                if (return_datetime - pickup_datetime) < min_duration:
                    messages.error(request, f"Hire duration must be at least {hire_settings.minimum_hire_duration_days} days.")
                    errors_exist = True

            if hire_settings and hire_settings.booking_lead_time_hours is not None:
                min_pickup_time = now + datetime.timedelta(hours=hire_settings.booking_lead_time_hours)
                if pickup_datetime < min_pickup_time:
                    messages.error(request, f"Pickup must be at least {hire_settings.booking_lead_time_hours} hours from now.")
                    errors_exist = True

            blocked_dates = BlockedHireDate.objects.filter(
                start_date__lte=return_date,
                end_date__gte=pickup_date
            ).exists()
            if blocked_dates:
                messages.error(request, "Selected dates overlap with a blocked hire period.")
                errors_exist = True

            # If any validation errors, redirect back to step2_choose_bike (which includes step1 form)
            if errors_exist:
                # We no longer store form data/errors in session as TempHireBooking will hold values
                return redirect('hire:step2_choose_bike')

            # --- Data Persistence to TempHireBooking ---
            temp_booking_id = request.session.get('temp_booking_id')
            temp_booking_uuid = request.session.get('temp_booking_uuid')
            temp_booking = None

            if temp_booking_id and temp_booking_uuid:
                try:
                    temp_booking = TempHireBooking.objects.get(
                        id=temp_booking_id,
                        session_uuid=temp_booking_uuid
                    )
                    # Update existing TempHireBooking
                    temp_booking.pickup_date = pickup_date
                    temp_booking.pickup_time = pickup_time
                    temp_booking.return_date = return_date
                    temp_booking.return_time = return_time
                    temp_booking.has_motorcycle_license = has_motorcycle_license
                    
                    # Link driver profile if user is authenticated and it's not already linked
                    if request.user.is_authenticated and hasattr(request.user, 'driver_profile') and temp_booking.driver_profile is None:
                        temp_booking.driver_profile = request.user.driver_profile
                    
                    temp_booking.save()
                    messages.success(request, "Booking dates updated.")

                except TempHireBooking.DoesNotExist:
                    messages.error(request, "Error retrieving temporary booking, creating a new one.")
                    # Clear session keys if the object was not found
                    if 'temp_booking_id' in request.session:
                        del request.session['temp_booking_id']
                    if 'temp_booking_uuid' in request.session:
                        del request.session['temp_booking_uuid']
                    temp_booking = None # Ensure temp_booking is None to trigger creation
                except Exception as e:
                    messages.error(request, f"An unexpected error occurred while updating your booking: {e}")
                    temp_booking = None # Ensure temp_booking is None to trigger creation

            # If no temporary booking exists or an error occurred retrieving it, create a new one
            if not temp_booking:
                driver_profile_for_temp_booking = None
                if request.user.is_authenticated:
                    try:
                        driver_profile_for_temp_booking = request.user.driver_profile
                    except DriverProfile.DoesNotExist:
                        # User is authenticated but doesn't have a DriverProfile yet,
                        # it will be created in Step 4.
                        pass

                temp_booking = TempHireBooking.objects.create(
                    session_uuid=uuid.uuid4(),
                    pickup_date=pickup_date,
                    pickup_time=pickup_time,
                    return_date=return_date,
                    return_time=return_time,
                    has_motorcycle_license=has_motorcycle_license,
                    driver_profile=driver_profile_for_temp_booking # Link driver profile here
                )
                request.session['temp_booking_id'] = temp_booking.id
                request.session['temp_booking_uuid'] = str(temp_booking.session_uuid)
                messages.success(request, "Booking dates saved.")
            
            # Redirect to step 2, passing the temp_booking_id in the URL
            # This is a better way to ensure continuity without relying on session for all data
            return redirect(reverse('hire:step2_choose_bike') + f'?temp_booking_id={temp_booking.id}&temp_booking_uuid={temp_booking.session_uuid}')

        else:
            # Form is not valid, add errors to messages and redirect
            messages.error(request, "Please correct the errors below for your hire dates and times.")
            # We no longer store form data/errors in session
            return redirect('hire:step2_choose_bike')

