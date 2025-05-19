# hire/views/step1_DateTime_view.py

import datetime
import uuid
from django.shortcuts import redirect
from django.views import View
from django.contrib import messages
from django.utils import timezone

from ..forms.step1_DateTime_form import Step1DateTimeForm
from ..models import  TempHireBooking
from dashboard.models import HireSettings, BlockedHireDate
# from inventory.models import Motorcycle # Not directly needed in this view anymore
from ..views.utils import calculate_hire_duration_days # Assuming you have this utility


class SelectDateTimeView(View):
    """
    Handles the submission of the Step 1 Date/Time/License form.
    This view is POST-only. It processes the form and redirects to Step 2.
    """

    # No get() method here. Accessing /hire/book/step1/select-datetime/ via GET
    # will result in a 405 Method Not Allowed, which is expected as this is
    # primarily a form submission endpoint.

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

            # --- Validation Checks (duplicate with form, but good for quick exit) ---
            if return_datetime <= pickup_datetime:
                 messages.error(request, "Return date and time must be after pickup date and time.")
                 # Store invalid form data and errors in session for Step 2 to pick up
                 request.session['step1_form_data'] = request.POST.dict()
                 request.session['step1_form_errors'] = form.errors.as_json()
                 return redirect('hire:step2_choose_bike')

            if hire_settings and hire_settings.minimum_hire_duration_days is not None:
                 min_duration = datetime.timedelta(days=hire_settings.minimum_hire_duration_days)
                 if (return_datetime - pickup_datetime) < min_duration:
                      messages.error(request, f"Hire duration must be at least {hire_settings.minimum_hire_duration_days} days.")
                      request.session['step1_form_data'] = request.POST.dict()
                      request.session['step1_form_errors'] = form.errors.as_json()
                      return redirect('hire:step2_choose_bike')

            if hire_settings and hire_settings.booking_lead_time_hours is not None:
                 min_pickup_time = now + datetime.timedelta(hours=hire_settings.booking_lead_time_hours)
                 if pickup_datetime < min_pickup_time:
                      messages.error(request, f"Pickup must be at least {hire_settings.booking_lead_time_hours} hours from now.")
                      request.session['step1_form_data'] = request.POST.dict()
                      request.session['step1_form_errors'] = form.errors.as_json()
                      return redirect('hire:step2_choose_bike')

            blocked_dates = BlockedHireDate.objects.filter(
                 start_date__lte=return_date,
                 end_date__gte=pickup_date
            ).exists()
            if blocked_dates:
                 messages.error(request, "Selected dates overlap with a blocked hire period.")
                 request.session['step1_form_data'] = request.POST.dict()
                 request.session['step1_form_errors'] = form.errors.as_json()
                 return redirect('hire:step2_choose_bike')

            # --- Update or Create TempHireBooking ---
            temp_booking_id = request.session.get('temp_booking_id')
            temp_booking_uuid = request.session.get('temp_booking_uuid')
            temp_booking = None

            if temp_booking_id and temp_booking_uuid:
                 try:
                      temp_booking = TempHireBooking.objects.get(
                           id=temp_booking_id,
                           session_uuid=temp_booking_uuid
                      )
                      temp_booking.pickup_date = pickup_date
                      temp_booking.pickup_time = pickup_time
                      temp_booking.return_date = return_date
                      temp_booking.return_time = return_time
                      temp_booking.has_motorcycle_license = has_motorcycle_license
                      temp_booking.save()
                      messages.success(request, "Booking dates updated.")

                 except TempHireBooking.DoesNotExist:
                      messages.error(request, "Error retrieving temporary booking, creating a new one.")
                      if 'temp_booking_id' in request.session:
                           del request.session['temp_booking_id']
                      if 'temp_booking_uuid' in request.session:
                           del request.session['temp_booking_uuid']

            if not temp_booking:
                 temp_booking = TempHireBooking.objects.create(
                      session_uuid=uuid.uuid4(),
                      pickup_date=pickup_date,
                      pickup_time=pickup_time,
                      return_date=return_date,
                      return_time=return_time,
                      has_motorcycle_license=has_motorcycle_license
                 )
                 request.session['temp_booking_id'] = temp_booking.id
                 request.session['temp_booking_uuid'] = str(temp_booking.session_uuid)
                 messages.success(request, "Booking dates saved.")

            # Clear any stale form data/errors from session after successful submission
            if 'step1_form_data' in request.session:
                 del request.session['step1_form_data']
            if 'step1_form_errors' in request.session:
                 del request.session['step1_form_errors']

            return redirect('hire:step2_choose_bike')

        else:
            # Form is not valid
            messages.error(request, "Please correct the errors below for your hire dates and times.")
            # Store invalid form data and errors in session for Step 2 to pick up
            request.session['step1_form_data'] = request.POST.dict()
            request.session['step1_form_errors'] = form.errors.as_json() # Store as JSON string
            return redirect('hire:step2_choose_bike')