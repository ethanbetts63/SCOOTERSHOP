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
    This view is POST-only. It processes the form, creates a new temporary
    booking, or updates an existing one, and redirects to Step 2.
    """

    def post(self, request, *args, **kwargs):
        # --- Clear session variables for a completely fresh start ---
        # This ensures that a new booking flow is initiated only when 'final_booking_reference' is present.
        # temp_booking_id and temp_booking_uuid are now handled by update/create logic below.
        if 'final_booking_reference' in request.session:
            del request.session['final_booking_reference']
            print("Cleared 'final_booking_reference' from session at the start of Step 1.")
        
        form = Step1DateTimeForm(request.POST)
        hire_settings = HireSettings.objects.first()

        print(f"--- Debugging SelectDateTimeView.post ---")
        print(f"Form data: {request.POST}")
        print(f"Hire Settings: {hire_settings}")
        print(f"Session temp_booking_id: {request.session.get('temp_booking_id')}")
        print(f"Session temp_booking_uuid: {request.session.get('temp_booking_uuid')}")


        if form.is_valid():
            pickup_date = form.cleaned_data['pick_up_date']
            pickup_time = form.cleaned_data['pick_up_time']
            return_date = form.cleaned_data['return_date']
            return_time = form.cleaned_data['return_time']
            has_motorcycle_license = form.cleaned_data['has_motorcycle_license']

            # Combine date and time, then make aware using the default timezone
            pickup_datetime_local = timezone.make_aware(datetime.datetime.combine(pickup_date, pickup_time))
            return_datetime_local = timezone.make_aware(datetime.datetime.combine(return_date, return_time))
            now_local = timezone.now()

            # Convert all datetimes to UTC for consistent comparison
            pickup_datetime_utc = pickup_datetime_local.astimezone(datetime.timezone.utc)
            return_datetime_utc = return_datetime_local.astimezone(datetime.timezone.utc)
            now_utc = now_local.astimezone(datetime.timezone.utc)

            # --- Validation Checks ---
            errors_exist = False
            # Rule: Hire duration must meet the minimum requirement.
            if hire_settings and hire_settings.minimum_hire_duration_hours is not None:
                min_duration = datetime.timedelta(hours=hire_settings.minimum_hire_duration_hours)
                actual_duration = return_datetime_utc - pickup_datetime_utc
                if actual_duration < min_duration:
                    messages.error(request, f"Hire duration must be at least {hire_settings.minimum_hire_duration_hours} hours.")
                    errors_exist = True

            # Rule: Hire duration must not exceed the maximum requirement.
            if hire_settings and hire_settings.maximum_hire_duration_days is not None:
                max_duration = datetime.timedelta(days=hire_settings.maximum_hire_duration_days)
                actual_duration = return_datetime_utc - pickup_datetime_utc
                if actual_duration > max_duration:
                    messages.error(request, f"Hire duration cannot exceed {hire_settings.maximum_hire_duration_days} days.")
                    errors_exist = True

            # Rule: Pickup must be at least 'booking_lead_time_hours' from now.
            if hire_settings and hire_settings.booking_lead_time_hours is not None:
                min_pickup_time_utc = now_utc + datetime.timedelta(hours=hire_settings.booking_lead_time_hours)
                if pickup_datetime_utc < min_pickup_time_utc:
                    messages.error(request, f"Pickup must be at least {hire_settings.booking_lead_time_hours} hours from now.")
                    errors_exist = True

            # Rule: Selected dates must not overlap with any blocked hire period.
            blocked_dates_overlap = BlockedHireDate.objects.filter(
                start_date__lte=return_date,
                end_date__gte=pickup_date
            ).exists()
            if blocked_dates_overlap:
                messages.error(request, "Selected dates overlap with a blocked hire period.")
                errors_exist = True

            if errors_exist:
                print(f"Redirecting back to step2_choose_bike due to view-level validation errors.")
                return redirect('hire:step2_choose_bike') 

            # --- Retrieve or Create TempHireBooking ---
            temp_booking = None
            temp_booking_id = request.session.get('temp_booking_id')
            temp_booking_uuid = request.session.get('temp_booking_uuid')

            if temp_booking_id and temp_booking_uuid:
                try:
                    temp_booking = TempHireBooking.objects.get(
                        id=temp_booking_id, 
                        session_uuid=temp_booking_uuid
                    )
                    print(f"Found existing TempHireBooking: ID {temp_booking.id}, UUID {temp_booking.session_uuid}")
                except TempHireBooking.DoesNotExist:
                    print(f"Existing TempHireBooking not found for ID {temp_booking_id}, UUID {temp_booking_uuid}. Will create new.")
                    temp_booking = None # Ensure it's None if not found

            driver_profile_for_temp_booking = None
            if request.user.is_authenticated:
                try:
                    driver_profile_for_temp_booking = request.user.driver_profile
                except DriverProfile.DoesNotExist:
                    print(f"Authenticated user {request.user.username} has no DriverProfile yet.")
                    pass

            try:
                if temp_booking:
                    # Update existing TempHireBooking
                    temp_booking.pickup_date = pickup_date
                    temp_booking.pickup_time = pickup_time
                    temp_booking.return_date = return_date
                    temp_booking.return_time = return_time
                    temp_booking.has_motorcycle_license = has_motorcycle_license
                    temp_booking.driver_profile = driver_profile_for_temp_booking # Update driver profile if available
                    temp_booking.save()
                    messages.success(request, "Dates updated. Please choose your motorcycle.")
                    print(f"Updated TempHireBooking: ID {temp_booking.id}, UUID {temp_booking.session_uuid}")
                else:
                    # Create new TempHireBooking
                    temp_booking = TempHireBooking.objects.create(
                        session_uuid=uuid.uuid4(), # Generate a new UUID for each new temp booking
                        pickup_date=pickup_date,
                        pickup_time=pickup_time,
                        return_date=return_date,
                        return_time=return_time,
                        has_motorcycle_license=has_motorcycle_license,
                        driver_profile=driver_profile_for_temp_booking
                    )
                    # Store the new temporary booking's ID and UUID in the session
                    request.session['temp_booking_id'] = temp_booking.id
                    request.session['temp_booking_uuid'] = str(temp_booking.session_uuid)
                    messages.success(request, "Dates selected. Please choose your motorcycle.")
                    print(f"New TempHireBooking created: ID {temp_booking.id}, UUID {temp_booking.session_uuid}")

                # Redirect to step 2, passing the new temp_booking_id and uuid
                redirect_url = reverse('hire:step2_choose_bike') + f'?temp_booking_id={temp_booking.id}&temp_booking_uuid={temp_booking.session_uuid}'
                print(f"Redirecting to: {redirect_url}")
                return redirect(redirect_url)

            except Exception as e:
                # Catch any unexpected errors during TempHireBooking creation/update
                messages.error(request, f"An unexpected error occurred while saving your selection: {e}")
                print(f"Error saving TempHireBooking: {e}")
                return redirect('hire:step2_choose_bike') # Redirect back if saving fails

        else:
            # Form is not valid.
            print(f"\nForm is NOT valid. Errors: {form.errors}")
            for error_list in form.errors.values():
                for error in error_list:
                    messages.error(request, error)
            # Redirect back to the page displaying the form (assumed to be step2_choose_bike or where step1_date_time_include.html is used)
            return redirect('hire:step2_choose_bike')

