# inventory/views/hire_motorcycle_list_view.py

from django.db.models import Q, Min, Max, Case, When, Value, DecimalField # Import Min, Max, Case, When, Value, DecimalField
import datetime
from django.contrib import messages
from django.utils import timezone # Import timezone
from datetime import timedelta # Import timedelta
from hire.models import HireBooking # Assuming HireBooking is in hire.models
from dashboard.models import HireSettings # Import HireSettings
from inventory.models import Motorcycle # Ensure Motorcycle is imported if needed for engine_size filter
from .motorcycle_list_view import MotorcycleListView # Import the base class
from dashboard.models import BlockedHireDate # Import BlockedHireDate
import logging # Import logging
from decimal import Decimal # Import Decimal

# Lists motorcycles available for hire
class HireMotorcycleListView(MotorcycleListView):
    template_name = 'inventory/hire.html'
    condition_name = 'hire'
    url_name = 'inventory:hire'

    # Adds hire-specific filtering (daily rate, date availability, engine size)
    def get_queryset(self):
        # Start by getting the base queryset
        queryset = super().get_queryset()

        # --- Handle Hire Date and Time Inputs and Validation ---
        pick_up_date_str = self.request.GET.get('pick_up_date')
        pick_up_time_str = self.request.GET.get('pick_up_time')
        return_date_str = self.request.GET.get('return_date')
        return_time_str = self.request.GET.get('return_time')
        has_motorcycle_license = self.request.GET.get('has_motorcycle_license') == 'true' # Get license status

        self.pick_up_datetime = None
        self.return_datetime = None
        self.duration_days = None # Store calculated duration in days

        # Store original inputs for re-populating the form on inventory/hire.html
        self.original_inputs = {
            'pick_up_date': pick_up_date_str,
            'pick_up_time': pick_up_time_str,
            'return_date': return_date_str,
            'return_time': return_time_str,
            'has_motorcycle_license': has_motorcycle_license # Store boolean status
        }

        # Fetch HireSettings for duration check
        hire_settings = None
        try:
            hire_settings = HireSettings.objects.first()
            if not hire_settings:
                messages.error(self.request, "Hire settings are not configured.")
                # Return empty queryset if essential settings are missing
                if pick_up_date_str and pick_up_time_str and return_date_str and return_time_str:
                     return self.model.objects.none()
                # If no dates selected, allow showing bikes but without availability/duration checks
                pass # Proceed with base queryset if no dates selected
        except Exception:
            messages.error(self.request, "Could not load hire settings.")
            if pick_up_date_str and pick_up_time_str and return_date_str and return_time_str:
                 return self.model.objects.none()
            pass # Proceed with base queryset if no dates selected


        # Only proceed with date/time validation and bike availability filtering if all four fields are present
        if pick_up_date_str and pick_up_time_str and return_date_str and return_time_str:
            try:
                # Parse dates
                pick_up_date = datetime.datetime.strptime(pick_up_date_str, '%Y-%m-%d').date()
                return_date = datetime.datetime.strptime(return_date_str, '%Y-%m-%d').date()

                # Parse times
                pick_up_time = datetime.datetime.strptime(pick_up_time_str, '%H:%M').time()
                return_time = datetime.datetime.strptime(return_time_str, '%H:%M').time()

                # Combine date and time into timezone-aware datetime objects
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
                    # Check if pickup or return datetime falls exactly on or within a blocked day
                    if blocked.start_date <= self.pick_up_datetime.date() <= blocked.end_date:
                         messages.error(self.request, f"Pickup date ({pick_up_date_str}) is not available due to a blocked period.")
                         return self.model.objects.none()

                    if blocked.start_date <= self.return_datetime.date() <= blocked.end_date:
                         messages.error(self.request, f"Return date ({return_date_str}) is not available due to a blocked period.")
                         return self.model.objects.none()


                # 3. Check Minimum and Maximum Hire Duration (Requires hire_settings)
                if hire_settings: # Only perform if hire_settings were loaded
                    duration = self.return_datetime - self.pick_up_datetime
                    duration_hours = duration.total_seconds() / 3600
                    duration_days_exact = duration_hours / 24 # Use exact calculation for comparison

                    if hire_settings.minimum_hire_duration_days is not None and duration_days_exact < hire_settings.minimum_hire_duration_days:
                         messages.error(self.request, f"Minimum hire duration is {hire_settings.minimum_hire_duration_days} days.")
                         return self.model.objects.none()

                    if hire_settings.maximum_hire_duration_days is not None and duration_days_exact > hire_settings.maximum_hire_duration_days:
                        messages.error(self.request, f"Maximum hire duration is {hire_settings.maximum_hire_duration_days} days.")
                        return self.model.objects.none()

                    # Store the duration in days (integer, for displaying "X days hire")
                    self.duration_days = duration.days # Use .days for whole days difference
                else:
                     messages.warning(self.request, "Hire duration could not be validated due to missing settings.")


                # 4. Check Booking Lead Time (Requires hire_settings)
                if hire_settings and hire_settings.booking_lead_time_hours is not None:
                    now = timezone.now()
                    min_pickup_time = now + timedelta(hours=hire_settings.booking_lead_time_hours)
                    if self.pick_up_datetime < min_pickup_time:
                        messages.error(self.request, f"Pickup must be at least {hire_settings.booking_lead_time_hours} hours from now.")
                        return self.model.objects.none()
                elif hire_settings:
                     messages.warning(self.request, "Booking lead time could not be validated due to missing settings.")


                # --- Apply Bike Availability Filtering ---

                # Find motorcycles booked within the validated datetime range
                conflicting_bookings = HireBooking.objects.filter(
                    status__in=['confirmed', 'pending'],
                    motorcycle__in=queryset, # Only consider motorcycles currently in the queryset
                ).filter(
                     # Check for overlapping datetime ranges
                     # A booking conflicts if its period starts before our return and ends after our pickup
                     Q(pickup_datetime__lt=self.return_datetime, return_datetime__gt=self.pick_up_datetime)
                ).values_list('motorcycle_id', flat=True)

                # Exclude motorcycles with conflicting bookings from the queryset
                queryset = queryset.exclude(id__in=conflicting_bookings)


            except ValueError:
                messages.error(self.request, "Invalid date or time format.")
                # Return empty queryset on error
                return self.model.objects.none()
            except Exception as e:
                messages.error(self.request, f"An unexpected error occurred during date processing: {e}")
                logging.exception("Error processing hire dates in HireMotorcycleListView")
                return self.model.objects.none()

        elif self.request.GET:
            # If GET request received but dates are missing (e.g., initial load after failed attempt or direct link)
            # If the user has submitted the form (i.e., there's a GET request with params), but the date fields are empty,
            # it implies they didn't select dates.
            # If there are other GET params but no dates, we should indicate dates are required for availability search.
             # Check if *any* expected hire search params are present (excluding page number etc.)
             hire_search_params = ['pick_up_date', 'pick_up_time', 'return_date', 'return_time', 'has_motorcycle_license', 'engine_size_lt', 'daily_rate_min', 'daily_rate_max']
             if any(param in self.request.GET for param in hire_search_params):
                 # If some hire search params are present but dates/times are missing, show an error
                 if not (pick_up_date_str and pick_up_time_str and return_date_str and return_time_str):
                     messages.info(self.request, "Please select both pickup and return dates and times to search for available motorcycles.")
                     return self.model.objects.none()
             # If no hire search params are present at all, it's likely the initial load of the inventory/hire page
             # In this case, we don't show an error but return an empty queryset as no search is performed yet.
             else:
                  # Return the base queryset without availability filtering on initial load
                  return super().get_queryset() # Or return empty if you don't want to show all bikes by default


        # --- Handle Engine Size Filtering ---
        # Determine the max engine size based on the license checkbox from the hire_book_include form
        # This filter is applied whether dates were successfully validated or not,
        # as it's based on the initial form submission.
        max_engine_size = 50 # Default for no license
        if has_motorcycle_license:
            max_engine_size = 2000 # Value for having a license (effectively 'any size')

        # Allow overriding the engine size filter if a specific value is provided in the search form on inventory/hire.html
        # Assuming an input field named 'engine_size_lt' exists on inventory/hire.html
        engine_size_lt_str = self.request.GET.get('engine_size_lt')
        if engine_size_lt_str:
             try:
                  # Use the value from the form on inventory/hire.html if provided and valid
                  max_engine_size = float(engine_size_lt_str)
             except (ValueError, TypeError):
                  messages.warning(self.request, "Invalid engine size value ignored.")
                  # Keep the max_engine_size derived from the license checkbox


        # Apply the engine size filter
        # Ensure Motorcycle model has an 'engine_size' field (DecimalField or IntegerField)
        try:
            # Assuming engine_size is stored as a number or can be cast to float/decimal
            queryset = queryset.filter(engine_size__lt=max_engine_size)
        except Exception as e:
            # Handle case where 'engine_size' field might not exist or filtering fails
            logging.error(f"Error filtering by engine size: {e}")
            messages.error(self.request, "Could not apply engine size filter.")
            # Decide whether to return empty or return without this filter applied
            # For now, let's proceed without this filter if it fails
            pass


        # --- Apply other filters (like daily rate) ---
        # Note: The price filter here applies to the *base* daily hire rate,
        # not the calculated discounted rate.
        daily_rate_min = self.request.GET.get('daily_rate_min')
        daily_rate_max = self.request.GET.get('daily_rate_max')

        try:
            if daily_rate_min:
                # Filter by the motorcycle's specific daily_hire_rate first
                queryset = queryset.filter(daily_hire_rate__gte=Decimal(daily_rate_min)) # Use Decimal
            if daily_rate_max:
                 # Filter by the motorcycle's specific daily_hire_rate first
                queryset = queryset.filter(daily_hire_rate__lte=Decimal(daily_rate_max)) # Use Decimal
        except (ValueError, TypeError):
             messages.warning(self.request, "Invalid daily rate value ignored.")
             pass


        return queryset


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add original inputs back to context to pre-fill the form on inventory/hire.html
        context['original_inputs'] = self.original_inputs

        # Add hire-specific context data
        if self.pick_up_datetime and self.return_datetime:
             # Pass formatted dates and times for displaying in the template
             context['pick_up_date'] = self.pick_up_datetime.strftime('%Y-%m-%d')
             context['pick_up_time'] = self.pick_up_datetime.strftime('%H:%M')
             context['return_date'] = self.return_datetime.strftime('%Y-%m-%d')
             context['return_time'] = self.return_datetime.strftime('%H:%M')
             context['hire_days'] = self.duration_days # Use the calculated integer duration
        else:
             # Pass empty strings or None if dates were not successfully validated
             context['pick_up_date'] = ''
             context['pick_up_time'] = ''
             context['return_date'] = ''
             context['return_time'] = ''
             context['hire_days'] = None


        # Pass blocked hire dates to the template for Flatpickr on inventory/hire.html
        blocked_hire_dates = BlockedHireDate.objects.all()
        blocked_hire_date_ranges = []
        for blocked in blocked_hire_dates:
             blocked_hire_date_ranges.append({
                 'from': blocked.start_date.strftime('%Y-%m-%d'),
                 'to': blocked.end_date.strftime('%Y-%m-%d')
             })
        import json
        context['blocked_hire_date_ranges_json'] = json.dumps(blocked_hire_date_ranges)

        # Pass the calculated max engine size based on the license status for pre-filling the engine size field
        # Or pass the license status itself, and handle the default value in the template's JS
        context['has_motorcycle_license'] = self.original_inputs.get('has_motorcycle_license', False) # Pass boolean status
        # Or calculate and pass the default engine size here:
        # default_engine_size_display = 2000 if context['has_motorcycle_license'] else 50
        # context['default_engine_size_display'] = default_engine_size_display


        # --- Calculate and Add Discounted Monthly Rate to Motorcycles ---
        hire_settings = None
        try:
            hire_settings = HireSettings.objects.first()
            context['hire_settings'] = hire_settings # Pass hire settings to template
        except Exception as e:
            logging.error(f"Error loading hire settings for price calculation: {e}")
            # Handle gracefully, perhaps set hire_settings to None

        # Iterate through the motorcycles in the context and calculate discounted rate
        if hire_settings and hire_settings.monthly_discount_percentage is not None:
            # Ensure calculation uses Decimal for correct arithmetic
            monthly_discount_factor = (Decimal(100) - hire_settings.monthly_discount_percentage) / Decimal(100)

            # Ensure context['motorcycles'] is a list or can be iterated and modified
            # The page_obj.object_list is the actual list of items for the current page
            if 'page_obj' in context and context['page_obj'] is not None:
                 motorcycles_list = context['page_obj'].object_list
            else:
                 # Fallback if not paginated or page_obj is None (shouldn't happen with pagination)
                 motorcycles_list = context.get('motorcycles', [])


            for motorcycle in motorcycles_list:
                base_daily_rate = None
                # Use the motorcycle's specific daily rate if available
                if motorcycle.daily_hire_rate is not None:
                    base_daily_rate = motorcycle.daily_hire_rate
                # Otherwise, use the default daily rate from settings
                elif hire_settings.default_daily_rate is not None:
                    base_daily_rate = hire_settings.default_daily_rate

                # Calculate discounted rate if a base daily rate exists
                if base_daily_rate is not None:
                    # Apply monthly discount
                    discounted_daily_rate = base_daily_rate * monthly_discount_factor
                    # Add the calculated rate to the motorcycle object
                    # Use a new attribute name to avoid conflicts
                    # Use quantize to maintain decimal places, falling back to 2 if base_daily_rate is from default (which has 2)
                    if isinstance(base_daily_rate, Decimal):
                         decimal_places = abs(base_daily_rate.as_tuple().exponent)
                    else:
                         # Assume default_daily_rate is Decimal with 2 places if base_daily_rate is not Decimal
                         decimal_places = 2

                    discounted_daily_rate = discounted_daily_rate.quantize(Decimal(10) ** -decimal_places)
                    motorcycle.monthly_discounted_daily_rate = discounted_daily_rate
                else:
                    # If no base daily rate, no discounted rate can be calculated
                    motorcycle.monthly_discounted_daily_rate = None
        else:
            # If hire settings or monthly discount is missing, set discounted rate to None for all bikes
            if 'page_obj' in context and context['page_obj'] is not None:
                 motorcycles_list = context['page_obj'].object_list
            else:
                 motorcycles_list = context.get('motorcycles', [])

            for motorcycle in motorcycles_list:
                 motorcycle.monthly_discounted_daily_rate = None


        # --- Calculate Min/Max Daily Rates for Price Filter Pre-fill ---
        min_price_prefill = None
        max_price_prefill = None

        # Get all motorcycles that are available for hire and have a daily rate (either specific or default)
        # Use annotate to add an 'effective_daily_rate' to each motorcycle in the queryset
        # This handles cases where a bike might not have a specific daily_hire_rate but the system has a default
        if hire_settings and hire_settings.default_daily_rate is not None:
             # Annotate with effective daily rate
             all_hire_motorcycles = Motorcycle.objects.filter(
                 is_available=True,
                 conditions__name='hire'
             ).annotate(
                 effective_daily_rate=Case(
                     When(daily_hire_rate__isnull=False, then='daily_hire_rate'),
                     default=hire_settings.default_daily_rate,
                     output_field=DecimalField()
                 )
             ).filter(effective_daily_rate__isnull=False) # Ensure we only consider bikes with an effective daily rate

             # Find the minimum and maximum effective daily rates
             rate_aggregation = all_hire_motorcycles.aggregate(min_rate=Min('effective_daily_rate'), max_rate=Max('effective_daily_rate'))

             min_effective_daily_rate = rate_aggregation.get('min_rate')
             max_effective_daily_rate = rate_aggregation.get('max_rate')

             if min_effective_daily_rate is not None:
                 # Apply monthly discount to the minimum rate
                 if hire_settings.monthly_discount_percentage is not None:
                      monthly_discount_factor = (Decimal(100) - hire_settings.monthly_discount_percentage) / Decimal(100)
                      min_price_prefill = min_effective_daily_rate * monthly_discount_factor
                      # Quantize to 2 decimal places for display
                      min_price_prefill = min_price_prefill.quantize(Decimal('0.01'))
                 else:
                      # If no monthly discount setting, min prefill is just the min rate
                      min_price_prefill = min_effective_daily_rate.quantize(Decimal('0.01')) # Quantize for display

             if max_effective_daily_rate is not None:
                 # Max prefill is simply the max effective daily rate
                 max_price_prefill = max_effective_daily_rate.quantize(Decimal('0.01')) # Quantize for display

        # Add the calculated pre-fill values to the context
        context['min_price_prefill'] = min_price_prefill
        context['max_price_prefill'] = max_price_prefill


        return context

