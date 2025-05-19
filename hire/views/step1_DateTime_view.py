# hire/views/step1_date_time_view.py (or add to hire/views.py)
import datetime
from django.shortcuts import redirect
from django.views import View
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
# Assuming HireSettings is in dashboard.models, adjust import if needed
from dashboard.models import HireSettings
# Assuming BlockedHireDate is in dashboard.models, adjust import if needed
from dashboard.models import BlockedHireDate

# Import the new form
from ..forms.step1_DateTime_form import Step1DateTimeForm

class SelectDateTimeView(View):
    # This view will handle the POST submission from the include form
    def post(self, request, *args, **kwargs):
        form = Step1DateTimeForm(request.POST)

        if form.is_valid():
            pickup_date = form.cleaned_data['pick_up_date']
            pickup_time = form.cleaned_data['pick_up_time']
            return_date = form.cleaned_data['return_date']
            return_time = form.cleaned_data['return_time']
            has_motorcycle_license = form.cleaned_data['has_motorcycle_license']

            # Combine date and time into datetime objects
            # Make them timezone aware if your project uses timezones
            pickup_datetime = timezone.make_aware(datetime.datetime.combine(pickup_date, pickup_time))
            return_datetime = timezone.make_aware(datetime.datetime.combine(return_date, return_time))

            # Perform additional validation (min/max duration, lead time, blocked dates)
            # This validation is similar to what's currently in HireMotorcycleListView's get_queryset
            # It's better to perform it *before* redirecting to the bike list page.
            hire_settings = HireSettings.objects.first() # Assuming a single settings object

            errors = []

            # Validate duration (can be basic here, detailed check is in bike list)
            if hire_settings:
                duration = return_datetime - pickup_datetime
                duration_days_exact = duration.total_seconds() / (24 * 3600)

                if hire_settings.minimum_hire_duration_days is not None and duration_days_exact < hire_settings.minimum_hire_duration_days:
                    errors.append(f"Minimum hire duration is {hire_settings.minimum_hire_duration_days} days.")

                if hire_settings.maximum_hire_duration_days is not None and duration_days_exact > hire_settings.maximum_hire_duration_days:
                     errors.append(f"Maximum hire duration is {hire_settings.maximum_hire_duration_days} days.")

                # Validate booking lead time
                if hire_settings.booking_lead_time_hours is not None:
                     now = timezone.now()
                     min_pickup_time = now + timedelta(hours=hire_settings.booking_lead_time_hours)
                     if pickup_datetime < min_pickup_time:
                          errors.append(f"Pickup must be at least {hire_settings.booking_lead_time_hours} hours from now.")

            # Check for blocked dates
            blocked_dates = BlockedHireDate.objects.all()
            for blocked in blocked_dates:
                 blocked_start_datetime = timezone.make_aware(datetime.datetime.combine(blocked.start_date, datetime.time.min))
                 blocked_end_datetime = timezone.make_aware(datetime.datetime.combine(blocked.end_date, datetime.time.max))

                 # Check for overlap
                 if (pickup_datetime <= blocked_end_datetime) and (return_datetime >= blocked_start_datetime):
                      errors.append(f"Your selected hire period conflicts with a blocked period ({blocked.start_date} to {blocked.end_date}).")
                      break # No need to check other blocked dates


            if errors:
                # If there are validation errors, add them to messages
                for error in errors:
                    messages.error(request, error)
                # Redirect back to the page where the form was submitted from
                # You might need a way to determine the referring URL, or redirect to a default page
                return redirect(request.META.get('HTTP_REFERER', '/')) # Redirect back or to homepage

            # If valid and no conflicts, store data in the session
            request.session['booking_pickup_datetime'] = pickup_datetime.isoformat()
            request.session['booking_return_datetime'] = return_datetime.isoformat()
            request.session['booking_has_motorcycle_license'] = has_motorcycle_license

            # Redirect to the motorcycle listing page (Step 2)
            # You can potentially add a success message here
            # messages.success(request, "Dates selected. Please choose a motorcycle.")
            return redirect('hire:step2_choose_bike') # This is the URL name for HireMotorcycleListView

        else:
            # If form is not valid (e.g., missing field), add form errors to messages
            for field, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, f"Error in {field}: {error}")

            # Redirect back to the page where the form was submitted from
            return redirect(request.META.get('HTTP_REFERER', '/')) # Redirect back or to homepage

    # Optional: Handle GET requests if someone lands directly on this URL (redirect them)
    def get(self, request, *args, **kwargs):
         return redirect('hire:step2_choose_bike') # Or a homepage etc.