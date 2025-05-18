# inventory/views/hire_motorcycle_list_view.py

from django.db.models import Q, Min, Max, Case, When, Value, DecimalField
import datetime
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from hire.models import HireBooking
from dashboard.models import HireSettings
from inventory.models import Motorcycle
from .motorcycle_list_view import MotorcycleListView
from dashboard.models import BlockedHireDate
import logging
from decimal import Decimal
import math

class HireMotorcycleListView(MotorcycleListView):
    template_name = 'inventory/hire.html'
    condition_name = 'hire'
    url_name = 'inventory:hire'

    def get_queryset(self):
        # Start with motorcycles available for hire
        queryset = Motorcycle.objects.filter(
            is_available=True,
            conditions__name='hire'
        )

        # Get hire date and time inputs from request
        pick_up_date_str = self.request.GET.get('hire_start_date')
        pick_up_time_str = self.request.GET.get('pick_up_time')
        return_date_str = self.request.GET.get('hire_end_date')
        return_time_str = self.request.GET.get('return_time')

        self.pick_up_datetime = None
        self.return_datetime = None
        self.duration_days = None

        # Store original inputs for form re-population
        has_motorcycle_license_str = self.request.GET.get('has_motorcycle_license')
        has_motorcycle_license = has_motorcycle_license_str == 'true'

        self.original_inputs = {
            'hire_start_date': pick_up_date_str,
            'pick_up_time': pick_up_time_str,
            'hire_end_date': return_date_str,
            'return_time': return_time_str,
            'has_motorcycle_license': has_motorcycle_license_str
        }

        # Fetch HireSettings
        hire_settings = None
        try:
            hire_settings = HireSettings.objects.first()
            if not hire_settings:
                messages.error(self.request, "Hire settings are not configured. Availability and pricing may be inaccurate.")
        except Exception:
            messages.error(self.request, "Could not load hire settings. Availability and pricing may be inaccurate.")
            pass

        # Process date/time inputs if all are provided
        if pick_up_date_str and pick_up_time_str and return_date_str and return_time_str:
            try:
                # Parse date and time strings
                pick_up_date = datetime.datetime.strptime(pick_up_date_str, '%Y-%m-%d').date()
                return_date = datetime.datetime.strptime(return_date_str, '%Y-%m-%d').date()
                pick_up_time = datetime.datetime.strptime(pick_up_time_str, '%H:%M').time()
                return_time = datetime.datetime.strptime(return_time_str, '%H:%M').time()

                # Combine into timezone-aware datetimes
                self.pick_up_datetime = timezone.make_aware(datetime.datetime.combine(pick_up_date, pick_up_time))
                self.return_datetime = timezone.make_aware(datetime.datetime.combine(return_date, return_time))

                # Validate return is after pickup
                if self.return_datetime <= self.pick_up_datetime:
                    messages.error(self.request, "Return date and time must be after pickup date and time.")
                    return self.model.objects.none()

                # Check for blocked dates
                blocked_dates = BlockedHireDate.objects.all()
                for blocked in blocked_dates:
                    blocked_start_datetime = timezone.make_aware(datetime.datetime.combine(blocked.start_date, datetime.time.min))
                    blocked_end_datetime = timezone.make_aware(datetime.datetime.combine(blocked.end_date, datetime.time.max))

                    # Check for overlap with blocked periods
                    if (self.pick_up_datetime <= blocked_end_datetime) and (self.return_datetime >= blocked_start_datetime):
                         messages.error(self.request, f"Your selected hire period conflicts with a blocked period ({blocked.start_date} to {blocked.end_date}).")
                         return self.model.objects.none()

                # Validate minimum and maximum hire duration using settings
                if hire_settings:
                    duration = self.return_datetime - self.pick_up_datetime
                    duration_hours = duration.total_seconds() / 3600
                    duration_days_exact = duration_hours / 24

                    if hire_settings.minimum_hire_duration_days is not None and duration_days_exact < hire_settings.minimum_hire_duration_days:
                         messages.error(self.request, f"Minimum hire duration is {hire_settings.minimum_hire_duration_days} days.")
                         return self.model.objects.none()

                    if hire_settings.maximum_hire_duration_days is not None and duration_days_exact > hire_settings.maximum_hire_duration_days:
                        messages.error(self.request, f"Maximum hire duration is {hire_settings.maximum_hire_duration_days} days.")
                        return self.model.objects.none()

                    self.duration_days = duration_days_exact
                else:
                     messages.warning(self.request, "Hire duration could not be validated due to missing settings.")

                # Validate booking lead time
                if hire_settings and hire_settings.booking_lead_time_hours is not None:
                    now = timezone.now()
                    min_pickup_time = now + timedelta(hours=hire_settings.booking_lead_time_hours)
                    if self.pick_up_datetime < min_pickup_time:
                        messages.error(self.request, f"Pickup must be at least {hire_settings.booking_lead_time_hours} hours from now.")
                        return self.model.objects.none()
                elif hire_settings:
                     messages.warning(self.request, "Booking lead time could not be validated due to missing settings.")

                # Exclude motorcycles with conflicting confirmed/pending bookings
                conflicting_bookings = HireBooking.objects.filter(
                    status__in=['confirmed', 'pending'],
                    motorcycle__in=queryset,
                ).filter(
                     Q(pickup_datetime__lt=self.return_datetime, return_datetime__gt=self.pick_up_datetime)
                ).values_list('motorcycle_id', flat=True)

                queryset = queryset.exclude(id__in=conflicting_bookings)

            except ValueError:
                messages.error(self.request, "Invalid date or time format.")
                return self.model.objects.none()
            except Exception as e:
                messages.error(self.request, f"An unexpected error occurred during date processing: {e}")
                return self.model.objects.none()
        # Inform user if date/time are missing but other filters are present
        elif self.request.GET:
            other_hire_search_params_with_values = [
                 param for param in ['price_min', 'price_max', 'seats', 'engine_size', 'has_motorcycle_license']
                 if self.request.GET.get(param)
            ]
            if other_hire_search_params_with_values:
                 messages.info(self.request, "Please select both pickup and return dates and times for availability checking. Showing all hire motorcycles matching other criteria.")

        # Apply engine size filtering based on input or license status
        engine_size_str = self.request.GET.get('engine_size')
        if engine_size_str:
             try:
                  max_engine_size_filter_value = float(engine_size_str)
                  queryset = queryset.filter(engine_size__lte=max_engine_size_filter_value)
             except (ValueError, TypeError):
                  messages.warning(self.request, "Invalid engine size value ignored.")
        else:
             has_motorcycle_license_str = self.request.GET.get('has_motorcycle_license')
             if has_motorcycle_license_str == 'false':
                  queryset = queryset.filter(engine_size__lte=50)

        # Apply seats filtering
        seats_str = self.request.GET.get('seats')
        if seats_str:
            try:
                seats_count = int(seats_str)
                queryset = queryset.filter(seats=seats_count)
            except (ValueError, TypeError):
                messages.warning(self.request, "Invalid number of seats value ignored.")
                pass

        # Apply daily rate (price) filtering
        daily_rate_min_str = self.request.GET.get('price_min')
        daily_rate_max_str = self.request.GET.get('price_max')

        try:
            # Annotate with effective daily rate if hire settings exist
            if hire_settings and hire_settings.default_daily_rate is not None:
                 queryset = queryset.annotate(
                     effective_daily_rate=Case(
                         When(daily_hire_rate__isnull=False, then='daily_hire_rate'),
                         default=hire_settings.default_daily_rate,
                         output_field=DecimalField()
                     )
                 )

            # Filter by minimum price
            if daily_rate_min_str:
                 if 'effective_daily_rate' in queryset.query.annotations:
                     queryset = queryset.filter(effective_daily_rate__gte=Decimal(daily_rate_min_str))
                 elif hire_settings and hire_settings.default_daily_rate is not None:
                      queryset = queryset.filter(Q(daily_hire_rate__gte=Decimal(daily_rate_min_str)) | Q(daily_hire_rate__isnull=True, effective_daily_rate__gte=Decimal(daily_rate_min_str)))
                 else:
                      queryset = queryset.filter(daily_hire_rate__gte=Decimal(daily_rate_min_str))

            # Filter by maximum price
            if daily_rate_max_str:
                 if 'effective_daily_rate' in queryset.query.annotations:
                      queryset = queryset.filter(effective_daily_rate__lte=Decimal(daily_rate_max_str))
                 elif hire_settings and hire_settings.default_daily_rate is not None:
                      queryset = queryset.filter(Q(daily_hire_rate__lte=Decimal(daily_rate_max_str)) | Q(daily_hire_rate__isnull=True, effective_daily_rate__lte=Decimal(daily_rate_max_str)))
                 else:
                      queryset = queryset.filter(daily_hire_rate__lte=Decimal(daily_rate_max_str))

        except (ValueError, TypeError):
             messages.warning(self.request, "Invalid daily rate value ignored.")
             pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add original inputs for form pre-population
        context['original_inputs'] = self.original_inputs

        # Add hire-specific context data if dates were validated
        if self.pick_up_datetime and self.return_datetime and self.duration_days is not None:
             context['pick_up_date'] = self.pick_up_datetime.strftime('%Y-%m-%d')
             context['pick_up_time'] = self.pick_up_datetime.strftime('%H:%M')
             context['return_date'] = self.return_datetime.strftime('%Y-%m-%d')
             context['return_time'] = self.return_datetime.strftime('%H:%M')
             context['hire_days'] = math.ceil(self.duration_days) if self.duration_days is not None else None
             context['hire_start_date'] = self.pick_up_datetime.date().strftime('%Y-%m-%d')
             context['hire_end_date'] = self.return_datetime.date().strftime('%Y-%m-%d')
        else:
             context['pick_up_date'] = ''
             context['pick_up_time'] = ''
             context['return_date'] = ''
             context['return_time'] = ''
             context['hire_days'] = None
             context['hire_start_date'] = None
             context['hire_end_date'] = None

        # Pass blocked hire dates for frontend date picker
        blocked_hire_dates = BlockedHireDate.objects.all()
        blocked_hire_date_ranges = []
        for blocked in blocked_hire_dates:
             blocked_hire_date_ranges.append({
                 'from': blocked.start_date.strftime('%Y-%m-%d'),
                 'to': blocked.end_date.strftime('%Y-%m-%d')
             })
        import json
        context['blocked_hire_date_ranges_json'] = json.dumps(blocked_hire_date_ranges)

        # Pass motorcycle license status for default engine size logic in template
        context['has_motorcycle_license'] = self.original_inputs.get('has_motorcycle_license', 'false') == 'true'

        # Fetch hire settings again for context
        hire_settings = None
        try:
            hire_settings = HireSettings.objects.first()
            context['hire_settings'] = hire_settings
        except Exception as e:
             logging.error(f"Error loading hire settings for price calculation: {e}")

        # Get the list of motorcycles being displayed
        motorcycles_list = context.get('page_obj').object_list if context.get('page_obj') else context.get('object_list', [])

        # Get IDs of motorcycles on the current page
        motorcycle_ids_on_page = [motorcycle.id for motorcycle in motorcycles_list]

        # Fetch motorcycles with effective daily rate annotation
        if hire_settings and hire_settings.default_daily_rate is not None:
             annotated_motorcycles_queryset = Motorcycle.objects.filter(id__in=motorcycle_ids_on_page).annotate(
                 effective_daily_rate=Case(
                     When(daily_hire_rate__isnull=False, then='daily_hire_rate'),
                     default=hire_settings.default_daily_rate,
                     output_field=DecimalField()
                 )
             )
        else:
             annotated_motorcycles_queryset = Motorcycle.objects.filter(id__in=motorcycle_ids_on_page)

        # Map annotated motorcycles by ID
        annotated_motorcycle_map = {motorcycle.id: motorcycle for motorcycle in annotated_motorcycles_queryset}

        # Update motorcycles in list with annotated data and calculate prices
        updated_motorcycles_list = []
        for motorcycle in motorcycles_list:
             # Use annotated object if available
             current_motorcycle = annotated_motorcycle_map.get(motorcycle.id, motorcycle)

             # Determine the base daily rate
             base_daily_rate = None
             if hasattr(current_motorcycle, 'effective_daily_rate') and current_motorcycle.effective_daily_rate is not None:
                  base_daily_rate = current_motorcycle.effective_daily_rate
             elif current_motorcycle.daily_hire_rate is not None:
                 base_daily_rate = current_motorcycle.daily_hire_rate
             elif hire_settings and hire_settings.default_daily_rate is not None:
                 base_daily_rate = hire_settings.default_daily_rate

             # Calculate discounted monthly rate
             if base_daily_rate is not None and hire_settings and hire_settings.monthly_discount_percentage is not None:
                 monthly_discount_factor = (Decimal(100) - hire_settings.monthly_discount_percentage) / Decimal(100)
                 discounted_daily_rate = base_daily_rate * monthly_discount_factor
                 if isinstance(base_daily_rate, Decimal):
                      decimal_places = abs(base_daily_rate.as_tuple().exponent)
                 else:
                      decimal_places = 2
                 current_motorcycle.monthly_discounted_daily_rate = discounted_daily_rate.quantize(Decimal(10) ** -decimal_places)
             else:
                 current_motorcycle.monthly_discounted_daily_rate = None

             # Calculate total hire price if dates are valid
             if self.pick_up_datetime and self.return_datetime and base_daily_rate is not None and self.duration_days is not None:
                  total_price = base_daily_rate * Decimal(str(self.duration_days))
                  current_motorcycle.total_hire_price = total_price.quantize(Decimal('0.01'))
             else:
                  current_motorcycle.total_hire_price = None

             updated_motorcycles_list.append(current_motorcycle)

        # Update the list of motorcycles in the context
        if 'page_obj' in context and context['page_obj'] is not None:
             context['page_obj'].object_list = updated_motorcycles_list
        else:
             context['motorcycles'] = updated_motorcycles_list

        # Calculate min/max daily rates for price filter pre-fill
        min_price_prefill = None
        max_price_prefill = None

        # Get all available hire motorcycles with rates
        initial_hire_queryset = self.model.objects.filter(
            is_available=True,
            conditions__name='hire'
        )

        if hire_settings and hire_settings.default_daily_rate is not None:
             all_hire_motorcycles_with_rates = initial_hire_queryset.annotate(
                 effective_daily_rate=Case(
                     When(daily_hire_rate__isnull=False, then='daily_hire_rate'),
                     default=hire_settings.default_daily_rate,
                     output_field=DecimalField()
                 )
             ).filter(effective_daily_rate__isnull=False)

             rate_aggregation = all_hire_motorcycles_with_rates.aggregate(min_rate=Min('effective_daily_rate'), max_rate=Max('effective_daily_rate'))

             min_effective_daily_rate = rate_aggregation.get('min_rate')
             max_effective_daily_rate = rate_aggregation.get('max_rate')

             if min_effective_daily_rate is not None:
                  if hire_settings.monthly_discount_percentage is not None:
                       monthly_discount_factor = (Decimal(100) - hire_settings.monthly_discount_percentage) / Decimal(100)
                       min_price_prefill = min_effective_daily_rate * monthly_discount_factor
                       min_price_prefill = min_price_prefill.quantize(Decimal('0.01'))
                  else:
                       min_price_prefill = min_effective_daily_rate.quantize(Decimal('0.01'))

             if max_effective_daily_rate is not None:
                  max_price_prefill = max_effective_daily_rate.quantize(Decimal('0.01'))
        elif initial_hire_queryset.filter(daily_hire_rate__isnull=False).exists():
             rate_aggregation = initial_hire_queryset.filter(daily_hire_rate__isnull=False).aggregate(min_rate=Min('daily_hire_rate'), max_rate=Max('daily_hire_rate'))
             min_price_prefill = rate_aggregation.get('min_rate').quantize(Decimal('0.01')) if rate_aggregation.get('min_rate') else None
             max_price_prefill = rate_aggregation.get('max_rate').quantize(Decimal('0.01')) if rate_aggregation.get('max_rate') else None

        # Add price pre-fill values to context
        context['min_price_prefill'] = min_price_prefill
        context['max_price_prefill'] = max_price_prefill

        return context