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

        print(f"--- Debugging SelectDateTimeView.post ---")
        print(f"Form data: {request.POST}")
        print(f"Hire Settings: {hire_settings}")
        if hire_settings:
            print(f"  Min Hire Duration Days: {hire_settings.minimum_hire_duration_days}")
            print(f"  Max Hire Duration Days: {hire_settings.maximum_hire_duration_days}")
            print(f"  Booking Lead Time Hours: {hire_settings.booking_lead_time_hours}")
            print(f"  Pick Up Start Time: {hire_settings.pick_up_start_time}")
            print(f"  Pick Up End Time: {hire_settings.pick_up_end_time}")
            print(f"  Return Off Start Time: {hire_settings.return_off_start_time}")
            print(f"  Return End Time: {hire_settings.return_end_time}")


        if form.is_valid():
            pickup_date = form.cleaned_data['pick_up_date']
            pickup_time = form.cleaned_data['pick_up_time']
            return_date = form.cleaned_data['return_date']
            return_time = form.cleaned_data['return_time']
            has_motorcycle_license = form.cleaned_data['has_motorcycle_license']

            # Combine date and time, then make aware using the default timezone
            # Then convert all datetimes to UTC for consistent comparison
            pickup_datetime_local = timezone.make_aware(datetime.datetime.combine(pickup_date, pickup_time))
            return_datetime_local = timezone.make_aware(datetime.datetime.combine(return_date, return_time))
            now_local = timezone.now() # This is already aware, usually UTC or TIME_ZONE

            # Convert all datetimes to UTC for consistent comparison
            pickup_datetime_utc = pickup_datetime_local.astimezone(timezone.utc)
            return_datetime_utc = return_datetime_local.astimezone(timezone.utc)
            now_utc = now_local.astimezone(timezone.utc) # Ensure now is also explicitly UTC

            print(f"\nParsed Dates & Times:")
            print(f"  Pickup Date: {pickup_date}, Time: {pickup_time}")
            print(f"  Return Date: {return_date}, Time: {return_time}")
            print(f"  Pickup Datetime (local): {pickup_datetime_local}")
            print(f"  Return Datetime (local): {return_datetime_local}")
            print(f"  Current Datetime (local): {now_local}")
            print(f"  Pickup Datetime (UTC for comparison): {pickup_datetime_utc}")
            print(f"  Return Datetime (UTC for comparison): {return_datetime_utc}")
            print(f"  Current Datetime (UTC for comparison): {now_utc}")


            # --- Validation Checks ---
            errors_exist = False

            # Rule: Return date and time must be after pickup date and time.
            print(f"\nValidation: Return Datetime vs Pickup Datetime")
            print(f"  return_datetime_utc ({return_datetime_utc}) <= pickup_datetime_utc ({pickup_datetime_utc})? {return_datetime_utc <= pickup_datetime_utc}")
            if return_datetime_utc <= pickup_datetime_utc:
                messages.error(request, "Return date and time must be after pickup date and time.")
                errors_exist = True

            # Rule: Hire duration must meet the minimum requirement.
            if hire_settings and hire_settings.minimum_hire_duration_days is not None:
                min_duration = datetime.timedelta(days=hire_settings.minimum_hire_duration_days)
                actual_duration = return_datetime_utc - pickup_datetime_utc
                print(f"\nValidation: Minimum Hire Duration")
                print(f"  Minimum Hire Duration (timedelta): {min_duration}")
                print(f"  Actual Hire Duration (timedelta): {actual_duration}")
                print(f"  actual_duration ({actual_duration}) < min_duration ({min_duration})? {actual_duration < min_duration}")
                if actual_duration < min_duration:
                    messages.error(request, f"Hire duration must be at least {hire_settings.minimum_hire_duration_days} days.")
                    errors_exist = True

            # Rule: Hire duration must not exceed the maximum requirement.
            if hire_settings and hire_settings.maximum_hire_duration_days is not None:
                max_duration = datetime.timedelta(days=hire_settings.maximum_hire_duration_days)
                actual_duration = return_datetime_utc - pickup_datetime_utc # Recalculate or reuse from above
                print(f"\nValidation: Maximum Hire Duration")
                print(f"  Maximum Hire Duration (timedelta): {max_duration}")
                print(f"  Actual Hire Duration (timedelta): {actual_duration}")
                print(f"  actual_duration ({actual_duration}) > max_duration ({max_duration})? {actual_duration > max_duration}")
                if actual_duration > max_duration:
                    messages.error(request, f"Hire duration cannot exceed {hire_settings.maximum_hire_duration_days} days.")
                    errors_exist = True

            # Rule: Pickup must be at least 'booking_lead_time_hours' from now.
            if hire_settings and hire_settings.booking_lead_time_hours is not None:
                min_pickup_time_utc = now_utc + datetime.timedelta(hours=hire_settings.booking_lead_time_hours)
                print(f"\nValidation: Booking Lead Time")
                print(f"  Minimum Pickup Time (calculated UTC): {min_pickup_time_utc}")
                print(f"  pickup_datetime_utc ({pickup_datetime_utc}) < min_pickup_time_utc ({min_pickup_time_utc})? {pickup_datetime_utc < min_pickup_time_utc}")
                if pickup_datetime_utc < min_pickup_time_utc:
                    messages.error(request, f"Pickup must be at least {hire_settings.booking_lead_time_hours} hours from now.")
                    errors_exist = True

            # Rule: Selected dates must not overlap with any blocked hire period.
            blocked_dates_overlap = BlockedHireDate.objects.filter(
                start_date__lte=return_date, # These are date objects, not datetimes, so comparison is fine
                end_date__gte=pickup_date
            ).exists()
            print(f"\nValidation: Blocked Dates")
            print(f"  Checking for blocked dates between {pickup_date} and {return_date}.")
            print(f"  Blocked dates overlap found: {blocked_dates_overlap}")
            if blocked_dates_overlap:
                messages.error(request, "Selected dates overlap with a blocked hire period.")
                errors_exist = True

            print(f"\nErrors exist after all validations: {errors_exist}")

            # If any validation errors, redirect back to step2_choose_bike (which includes step1 form)
            if errors_exist:
                # We no longer store form data/errors in session as TempHireBooking will hold values
                print(f"Redirecting back to step2_choose_bike due to errors.")
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
                    print(f"Existing TempHireBooking updated: {temp_booking.id}")

                except TempHireBooking.DoesNotExist:
                    messages.error(request, "Error retrieving temporary booking, creating a new one.")
                    # Clear session keys if the object was not found
                    if 'temp_booking_id' in request.session:
                        del request.session['temp_booking_id']
                    if 'temp_booking_uuid' in request.session:
                        del request.session['temp_booking_uuid']
                    temp_booking = None # Ensure temp_booking is None to trigger creation
                    print(f"TempHireBooking not found, clearing session and preparing to create new.")
                except Exception as e:
                    messages.error(request, f"An unexpected error occurred while updating your booking: {e}")
                    temp_booking = None # Ensure temp_booking is None to trigger creation
                    print(f"Error updating TempHireBooking: {e}")

            # If no temporary booking exists or an error occurred retrieving it, create a new one
            if not temp_booking:
                driver_profile_for_temp_booking = None
                if request.user.is_authenticated:
                    try:
                        driver_profile_for_temp_booking = request.user.driver_profile
                    except DriverProfile.DoesNotExist:
                        # User is authenticated but doesn't have a DriverProfile yet,
                        # it will be created in Step 4.
                        print(f"Authenticated user has no DriverProfile yet.")
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
                print(f"New TempHireBooking created: {temp_booking.id}")
            
            # Redirect to step 2, passing the temp_booking_id in the URL
            # This is a better way to ensure continuity without relying on session for all data
            redirect_url = reverse('hire:step2_choose_bike') + f'?temp_booking_id={temp_booking.id}&temp_booking_uuid={temp_booking.session_uuid}'
            print(f"Redirecting to: {redirect_url}")
            return redirect(redirect_url)

        else:
            # Form is not valid, add errors to messages and redirect
            print(f"\nForm is NOT valid. Errors: {form.errors}")
            messages.error(request, "Please correct the errors below for your hire dates and times.")
            # We no longer store form data/errors in session
            return redirect('hire:step2_choose_bike')

