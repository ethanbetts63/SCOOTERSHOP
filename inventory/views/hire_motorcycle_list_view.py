# inventory/views/hire_motorcycle_list_view.py

from django.db.models import Q
import datetime
from django.contrib import messages
from django.utils import timezone # Import timezone
from datetime import timedelta # Import timedelta
from hire.models import HireBooking # Assuming HireBooking is in hire.models
from dashboard.models import HireSettings # Import HireSettings
from .motorcycle_list_view import MotorcycleListView # Import the base class
from dashboard.models import BlockedHireDate # Import BlockedHireDate

# Lists motorcycles available for hire
class HireMotorcycleListView(MotorcycleListView):
    template_name = 'inventory/hire.html'
    condition_name = 'hire'
    url_name = 'inventory:hire'

    # Adds hire-specific filtering (daily rate, date availability)
    def get_queryset(self):
        # Start by getting the base queryset
        queryset = super().get_queryset()

        # --- Handle Hire Date and Time Inputs and Validation ---
        pick_up_date_str = self.request.GET.get('pick_up_date')
        pick_up_time_str = self.request.GET.get('pick_up_time')
        return_date_str = self.request.GET.get('return_date')
        return_time_str = self.request.GET.get('return_time')

        self.pick_up_datetime = None
        self.return_datetime = None
        self.duration_days = None # Store calculated duration in days

        # Store original inputs for re-populating the form
        self.original_inputs = {
            'pick_up_date': pick_up_date_str,
            'pick_up_time': pick_up_time_str,
            'return_date': return_date_str,
            'return_time': return_time_str,
            'has_motorcycle_license': self.request.GET.get('has_motorcycle_license') == 'true' # Handle checkbox
        }

        # Fetch HireSettings
        try:
            hire_settings = HireSettings.objects.first() # Assuming singleton pattern or get the first one
            if not hire_settings:
                 messages.error(self.request, "Hire settings are not configured.")
                 return self.model.objects.none()
        except Exception:
            messages.error(self.request, "Could not load hire settings.")
            return self.model.objects.none()


        # Only proceed with date/time validation if all four fields are present
        if pick_up_date_str and pick_up_time_str and return_date_str and return_time_str:
            try:
                # Parse dates
                pick_up_date = datetime.datetime.strptime(pick_up_date_str, '%Y-%m-%d').date()
                return_date = datetime.datetime.strptime(return_date_str, '%Y-%m-%d').date()

                # Parse times
                pick_up_time = datetime.datetime.strptime(pick_up_time_str, '%H:%M').time()
                return_time = datetime.datetime.strptime(return_time_str, '%H:%M').time()

                # Combine date and time into timezone-aware datetime objects
                # Assuming timezone is configured in settings.py
                self.pick_up_datetime = timezone.make_aware(datetime.datetime.combine(pick_up_date, pick_up_time))
                self.return_datetime = timezone.make_aware(datetime.datetime.combine(return_date, return_time))

                # --- Perform Date and Time Validations ---

                # 1. Check if return is after pickup
                if self.return_datetime <= self.pick_up_datetime:
                    messages.error(self.request, "Return date and time must be after pickup date and time.")
                    return self.model.objects.none()

                # 2. Check for Blocked Dates
                blocked_dates = BlockedHireDate.objects.all()
                for blocked in blocked_dates:
                    blocked_start = timezone.make_aware(datetime.datetime.combine(blocked.start_date, datetime.time.min))
                    blocked_end = timezone.make_aware(datetime.datetime.combine(blocked.end_date, datetime.time.max))

                    # Check if pickup date/time is within a blocked range
                    if blocked_start <= self.pick_up_datetime <= blocked_end:
                        messages.error(self.request, f"Pickup date ({pick_up_date_str}) is not available due to a blocked period.")
                        return self.model.objects.none()

                    # Check if return date/time is within a blocked range
                    if blocked_start <= self.return_datetime <= blocked_end:
                        messages.error(self.request, f"Return date ({return_date_str}) is not available due to a blocked period.")
                        return self.model.objects.none()


                # 3. Check Minimum and Maximum Hire Duration
                duration = self.return_datetime - self.pick_up_datetime
                # Calculate duration in days, including fractions
                duration_hours = duration.total_seconds() / 3600
                duration_days_exact = duration_hours / 24

                if hire_settings.minimum_hire_duration_days is not None and duration_days_exact < hire_settings.minimum_hire_duration_days:
                     messages.error(self.request, f"Minimum hire duration is {hire_settings.minimum_hire_duration_days} days.")
                     return self.model.objects.none()

                if hire_settings.maximum_hire_duration_days is not None and duration_days_exact > hire_settings.maximum_hire_duration_days:
                    messages.error(self.request, f"Maximum hire duration is {hire_settings.maximum_hire_duration_days} days.")
                    return self.model.objects.none()

                # Store the duration in days (integer, for displaying "X days hire")
                self.duration_days = duration.days # Use .days for whole days difference

                # 4. Check Booking Lead Time
                now = timezone.now()
                min_pickup_time = now + timedelta(hours=hire_settings.booking_lead_time_hours)
                if self.pick_up_datetime < min_pickup_time:
                    messages.error(self.request, f"Pickup must be at least {hire_settings.booking_lead_time_hours} hours from now.")
                    return self.model.objects.none()


                # --- Proceed with Bike Availability Filtering if Dates are Valid ---

                # Find motorcycles booked within the validated date range
                # Updated Q object to use datetime fields and check overlap
                conflicting_bookings = HireBooking.objects.filter(
                    status__in=['confirmed', 'pending'],
                    # Only consider bookings for motorcycles that are currently in our filtered queryset
                    motorcycle__in=queryset,
                ).filter(
                     # Check for overlapping datetime ranges
                     Q(pickup_date__lte=self.return_datetime.date(), return_date__gte=self.pick_up_datetime.date()),
                     # Further refine by time if dates overlap
                     Q(pickup_datetime__lt=self.return_datetime, return_datetime__gt=self.pick_up_datetime) # Use < and > for strict overlap
                ).values_list('motorcycle_id', flat=True)

                # Exclude motorcycles with conflicting bookings from the queryset
                queryset = queryset.exclude(id__in=conflicting_bookings)


            except ValueError:
                messages.error(self.request, "Invalid date or time format.")
                return self.model.objects.none()
            except Exception as e:
                # Catch any other unexpected errors during date processing
                messages.error(self.request, f"An unexpected error occurred: {e}")
                # Log the exception for debugging
                import logging
                logging.exception("Error processing hire dates in HireMotorcycleListView")
                return self.model.objects.none()

        elif self.request.GET:
            # If GET request received but dates are missing (after initial load)
            # This might happen if the user searches without selecting dates
            messages.info(self.request, "Please select both pickup and return dates and times to search for available motorcycles.")
            # Return an empty queryset as no search criteria were provided
            return self.model.objects.none()

        # --- Apply other filters (like daily rate) after date validation ---
        daily_rate_min = self.request.GET.get('daily_rate_min')
        daily_rate_max = self.request.GET.get('daily_rate_max')

        try:
            if daily_rate_min:
                queryset = queryset.filter(daily_hire_rate__gte=float(daily_rate_min))
            if daily_rate_max:
                queryset = queryset.filter(daily_hire_rate__lte=float(daily_rate_max))
        except (ValueError, TypeError):
             messages.error(self.request, "Invalid daily rate value.")
             # Keep the existing queryset or return empty, depending on desired behavior for invalid rate
             # For now, let's just add the message and proceed with potentially valid dates
             pass


        return queryset


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add original inputs back to context to pre-fill the form
        context['original_inputs'] = self.original_inputs

        # Add hire-specific context data
        if self.pick_up_datetime and self.return_datetime:
             context['pick_up_date'] = self.pick_up_datetime.strftime('%Y-%m-%d')
             context['pick_up_time'] = self.pick_up_datetime.strftime('%H:%M') # Format for Flatpickr time input
             context['return_date'] = self.return_datetime.strftime('%Y-%m-%d')
             context['return_time'] = self.return_datetime.strftime('%H:%M') # Format for Flatpickr time input
             context['hire_days'] = self.duration_days # Use the calculated integer duration

        # Pass blocked hire dates to the template for Flatpickr
        blocked_hire_dates = BlockedHireDate.objects.all()
        blocked_hire_date_ranges = []
        for blocked in blocked_hire_dates:
             blocked_hire_date_ranges.append({
                 'from': blocked.start_date.strftime('%Y-%m-%d'),
                 'to': blocked.end_date.strftime('%Y-%m-%d')
             })
        import json
        context['blocked_hire_date_ranges_json'] = json.dumps(blocked_hire_date_ranges)

        # You can also pass HireSettings explicitly here if needed in the template,
        # although it's already available via the context processor
        # try:
        #      context['hire_settings'] = HireSettings.objects.first()
        # except Exception:
        #      pass # Handle exception


        return context