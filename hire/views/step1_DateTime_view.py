import datetime
import uuid
from django.shortcuts import redirect
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse

from ..forms.step1_DateTime_form import Step1DateTimeForm
from ..models import TempHireBooking, DriverProfile
from dashboard.models import HireSettings, BlockedHireDate


class SelectDateTimeView(View):

    def post(self, request, *args, **kwargs):
        if 'final_booking_reference' in request.session:
            del request.session['final_booking_reference']
        
        form = Step1DateTimeForm(request.POST)
        hire_settings = HireSettings.objects.first()


        if form.is_valid():
            pickup_date = form.cleaned_data['pick_up_date']
            pickup_time = form.cleaned_data['pick_up_time']
            return_date = form.cleaned_data['return_date']
            return_time = form.cleaned_data['return_time']
            has_motorcycle_license = form.cleaned_data['has_motorcycle_license']

            pickup_datetime_local = timezone.make_aware(datetime.datetime.combine(pickup_date, pickup_time))
            return_datetime_local = timezone.make_aware(datetime.datetime.combine(return_date, return_time))
            now_local = timezone.now()

            pickup_datetime_utc = pickup_datetime_local.astimezone(datetime.timezone.utc)
            return_datetime_utc = return_datetime_local.astimezone(datetime.timezone.utc)
            now_utc = now_local.astimezone(datetime.timezone.utc)

            errors_exist = False
            if hire_settings and hire_settings.minimum_hire_duration_hours is not None:
                min_duration = datetime.timedelta(hours=hire_settings.minimum_hire_duration_hours)
                actual_duration = return_datetime_utc - pickup_datetime_utc
                if actual_duration < min_duration:
                    messages.error(request, f"Hire duration must be at least {hire_settings.minimum_hire_duration_hours} hours.")
                    errors_exist = True

            if hire_settings and hire_settings.maximum_hire_duration_days is not None:
                max_duration = datetime.timedelta(days=hire_settings.maximum_hire_duration_days)
                actual_duration = return_datetime_utc - pickup_datetime_utc
                if actual_duration > max_duration:
                    messages.error(request, f"Hire duration cannot exceed {hire_settings.maximum_hire_duration_days} days.")
                    errors_exist = True

            if hire_settings and hire_settings.booking_lead_time_hours is not None:
                min_pickup_time_utc = now_utc + datetime.timedelta(hours=hire_settings.booking_lead_time_hours)
                if pickup_datetime_utc < min_pickup_time_utc:
                    messages.error(request, f"Pickup must be at least {hire_settings.booking_lead_time_hours} hours from now.")
                    errors_exist = True

            blocked_dates_overlap = BlockedHireDate.objects.filter(
                start_date__lte=return_date,
                end_date__gte=pickup_date
            ).exists()
            if blocked_dates_overlap:
                messages.error(request, "Selected dates overlap with a blocked hire period.")
                errors_exist = True

            if errors_exist:
                return redirect('hire:step2_choose_bike')

            temp_booking = None
            temp_booking_id = request.session.get('temp_booking_id')
            temp_booking_uuid = request.session.get('temp_booking_uuid')

            if temp_booking_id and temp_booking_uuid:
                try:
                    temp_booking = TempHireBooking.objects.get(
                        id=temp_booking_id,
                        session_uuid=temp_booking_uuid
                    )
                except TempHireBooking.DoesNotExist:
                    temp_booking = None

            driver_profile_for_temp_booking = None
            if request.user.is_authenticated:
                try:
                    driver_profile_for_temp_booking = request.user.driver_profile
                except DriverProfile.DoesNotExist:
                    pass

            try:
                if temp_booking:
                    temp_booking.pickup_date = pickup_date
                    temp_booking.pickup_time = pickup_time
                    temp_booking.return_date = return_date
                    temp_booking.return_time = return_time
                    temp_booking.has_motorcycle_license = has_motorcycle_license
                    temp_booking.driver_profile = driver_profile_for_temp_booking
                    temp_booking.save()
                    messages.success(request, "Dates updated. Please choose your motorcycle.")
                else:
                    temp_booking = TempHireBooking.objects.create(
                        session_uuid=uuid.uuid4(),
                        pickup_date=pickup_date,
                        pickup_time=pickup_time,
                        return_date=return_date,
                        return_time=return_time,
                        has_motorcycle_license=has_motorcycle_license,
                        driver_profile=driver_profile_for_temp_booking
                    )
                    request.session['temp_booking_id'] = temp_booking.id
                    request.session['temp_booking_uuid'] = str(temp_booking.session_uuid)
                    messages.success(request, "Dates selected. Please choose your motorcycle.")

                redirect_url = reverse('hire:step2_choose_bike') + f'?temp_booking_id={temp_booking.id}&temp_booking_uuid={temp_booking.session_uuid}'
                return redirect(redirect_url)

            except Exception as e:
                messages.error(request, f"An unexpected error occurred while saving your selection: {e}")
                return redirect('hire:step2_choose_bike')

        else:
            for error_list in form.errors.values():
                for error in error_list:
                    messages.error(request, error)
            return redirect('hire:step2_choose_bike')
