# hire/views/step2_BikeChoice_view.py

import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

from inventory.models import Motorcycle
from ..models import HireBooking, TempHireBooking
from dashboard.models import HireSettings, BlockedHireDate
from ..forms.step1_DateTime_form import Step1DateTimeForm
from ..views.utils import calculate_hire_price, calculate_hire_duration_days

class BikeChoiceView(View):
    template_name = 'hire/step2_choose_bike.html'
    paginate_by = 9

    def get(self, request, *args, **kwargs):
        temp_booking_id = request.session.get('temp_booking_id')
        temp_booking_uuid = request.session.get('temp_booking_uuid')
        temp_booking = None

        # --- 1. Retrieve Temporary Booking Details or Initialize Defaults ---
        if temp_booking_id and temp_booking_uuid:
            try:
                temp_booking = TempHireBooking.objects.get(
                    id=temp_booking_id,
                    session_uuid=temp_booking_uuid
                )
            except TempHireBooking.DoesNotExist:
                messages.error(request, "Your temporary booking could not be found or has expired. Please select your hire dates.")
                if 'temp_booking_id' in request.session:
                    del request.session['temp_booking_id']
                if 'temp_booking_uuid' in request.session:
                    del request.session['temp_booking_uuid']
                # Continue with default values as if accessed directly

        # If no temp_booking exists (direct access or expired), set default values
        # These will be used for the initial display and pre-filling the form.
        # They will *not* be saved to the database unless the Step 1 form is submitted.
        if not temp_booking or not (temp_booking.pickup_date and temp_booking.pickup_time and temp_booking.return_date and temp_booking.return_time):
            # Set sensible defaults for initial view
            now = timezone.now()
            default_pickup_date = now.date()
            default_pickup_time = now.time().replace(minute=0, second=0, microsecond=0) # Round to nearest hour
            # Ensure default return date is at least one day after pickup
            default_return_datetime = now + datetime.timedelta(days=1)
            default_return_date = default_return_datetime.date()
            default_return_time = default_return_datetime.time().replace(minute=0, second=0, microsecond=0)

            # Create a 'dummy' temp_booking object for consistent variable access
            # This is not saved to the DB at this point.
            temp_booking_display = TempHireBooking(
                pickup_date=default_pickup_date,
                pickup_time=default_pickup_time,
                return_date=default_return_date,
                return_time=default_return_time,
                has_motorcycle_license=True # Default to true for broader initial display
            )
            messages.info(request, "Please select your desired hire dates and times to view available motorcycles.")
        else:
            temp_booking_display = temp_booking # Use the actual temp_booking if it exists and is valid

        # Use temp_booking_display for calculations and form pre-filling
        pickup_datetime = timezone.make_aware(datetime.datetime.combine(temp_booking_display.pickup_date, temp_booking_display.pickup_time))
        return_datetime = timezone.make_aware(datetime.datetime.combine(temp_booking_display.return_date, temp_booking_display.return_time))
        has_license = temp_booking_display.has_motorcycle_license

        # Duration for pricing (using potentially default dates/times)
        duration_days = calculate_hire_duration_days(pickup_datetime, return_datetime)


        # --- 2. Filter Motorcycles ---
        available_motorcycles = Motorcycle.objects.filter(conditions__name='hire', is_available=True)

        if not has_license:
            available_motorcycles = available_motorcycles.filter(engine_size__lte=50)

        conflicting_bookings = HireBooking.objects.filter(
            Q(pickup_date__lt=return_datetime.date()) |
            (Q(pickup_date=return_datetime.date()) & Q(pickup_time__lte=return_datetime.time())),
            Q(return_date__gt=pickup_datetime.date()) |
            (Q(return_date=pickup_datetime.date()) & Q(return_time__gte=pickup_datetime.time())),
            status__in=['pending', 'confirmed', 'in_progress']
        )
        booked_motorcycle_ids = conflicting_bookings.values_list('motorcycle__id', flat=True)
        final_motorcycles_queryset = available_motorcycles.exclude(id__in=booked_motorcycle_ids)

        # --- 3. Add Price Calculations and Other Annotations ---
        hire_settings = HireSettings.objects.first()

        motorcycles_with_prices = []
        for motorcycle in final_motorcycles_queryset:
             base_daily_rate = motorcycle.daily_hire_rate or (hire_settings.default_daily_rate if hire_settings else 0)
             monthly_discount_factor = hire_settings.monthly_discount_percentage / 100 if hire_settings else 0
             discounted_daily_rate_for_display = base_daily_rate * (1 - monthly_discount_factor)

             total_hire_price_for_bike = calculate_hire_price(
                  motorcycle,
                  pickup_datetime,
                  return_datetime,
                  hire_settings
             )

             motorcycles_with_prices.append({
                  'object': motorcycle,
                  'daily_hire_rate_display': discounted_daily_rate_for_display,
                  'total_hire_price': total_hire_price_for_bike,
             })

        # --- 4. Sorting ---
        order_by = request.GET.get('order', 'price_low_to_high')
        if order_by == 'price_low_to_high':
             motorcycles_with_prices.sort(key=lambda x: x['total_hire_price'])
        elif order_by == 'price_high_to_low':
             motorcycles_with_prices.sort(key=lambda x: x['total_hire_price'], reverse=True)

        # --- 5. Pagination ---
        paginator = Paginator(motorcycles_with_prices, self.paginate_by)
        page_number = request.GET.get('page')

        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)


        # --- 6. Prepare Context ---
        context = {
            'motorcycles': page_obj.object_list,
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages(),
            'paginator': paginator,
            'current_order': order_by,
            'hire_settings': hire_settings,
            'hire_start_date': temp_booking_display.pickup_date,
            'hire_end_date': temp_booking_display.return_date,
            'original_inputs': { # Data to pre-fill the Step 1 include form
                'pick_up_date': temp_booking_display.pickup_date.isoformat(),
                'pick_up_time': temp_booking_display.pickup_time.strftime('%H:%M'),
                'return_date': temp_booking_display.return_date.isoformat(),
                'return_time': temp_booking_display.return_time.strftime('%H:%M'),
                'has_motorcycle_license': 'true' if temp_booking_display.has_motorcycle_license else 'false',
            },
            'temp_booking': temp_booking, # This will be the actual DB object if it exists, otherwise None
        }

        if not motorcycles_with_prices and temp_booking_display.pickup_date and temp_booking_display.return_date:
             context['no_bikes_message'] = (
                 f"No motorcycles found for hire from {temp_booking_display.pickup_date.strftime('%d %b %Y')} "
                 f"to {temp_booking_display.return_date.strftime('%d %b %Y')}."
             )

        return render(request, self.template_name, context)

# Dummy calculate_hire_price and calculate_hire_duration_days remain the same.
# Ensure your actual utility functions are robust.
def calculate_hire_price(motorcycle, pickup_datetime, return_datetime, hire_settings):
    """
    Placeholder for your actual hire price calculation logic.
    Should take the motorcycle, dates, and settings and return the total price.
    """
    duration_days = calculate_hire_duration_days(pickup_datetime, return_datetime)
    base_daily_rate = motorcycle.daily_hire_rate or hire_settings.default_daily_rate if hire_settings else 0
    # Add logic for weekly/monthly discounts if applicable
    total_price = base_daily_rate * duration_days
    return total_price

def calculate_hire_duration_days(pickup_datetime, return_datetime):
     """
     Placeholder for your actual hire duration calculation logic.
     Calculates the number of hire days.
     """
     # For this example, let's use a simple days difference + 1 if time extends
     duration = return_datetime - pickup_datetime
     days = duration.days
     # If the duration is positive but less than a full day, or crosses midnight, count as 1 day.
     if duration.total_seconds() > 0 and days == 0:
         days = 1
     elif duration.total_seconds() > 0 and return_datetime.time() > pickup_datetime.time():
         days += 1
     return days