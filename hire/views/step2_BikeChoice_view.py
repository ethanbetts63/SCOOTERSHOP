# hire/views/step2_BikeChoice_view.py

import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

from inventory.models import Motorcycle
from ..models import HireBooking, TempHireBooking # Ensure TempHireBooking is imported
from dashboard.models import HireSettings, BlockedHireDate
from ..forms.step1_DateTime_form import Step1DateTimeForm
from ..views.utils import calculate_hire_price, calculate_hire_duration_days

class BikeChoiceView(View):
    template_name = 'hire/step2_choose_bike.html'
    paginate_by = 9

    def get(self, request, *args, **kwargs):
        print("--- BikeChoiceView GET START ---")
        print(f"Session key: {request.session.session_key}")
        print(f"Session data at start: {request.session.items()}")

        temp_booking_id = request.session.get('temp_booking_id')
        temp_booking_uuid = request.session.get('temp_booking_uuid')
        temp_booking = None

        print(f"Retrieving session temp_booking_id: {temp_booking_id}, temp_booking_uuid: {temp_booking_uuid}")

        # --- 1. Retrieve Temporary Booking Details or Initialize Defaults ---
        if temp_booking_id and temp_booking_uuid:
            try:
                temp_booking = TempHireBooking.objects.get(
                    id=temp_booking_id,
                    session_uuid=temp_booking_uuid
                )
                print(f"Successfully retrieved TempHireBooking from session: ID={temp_booking.id}, UUID={temp_booking.session_uuid}")
                print(f"Retrieved TempBooking Dates: Pickup={temp_booking.pickup_date} {temp_booking.pickup_time}, Return={temp_booking.return_date} {temp_booking.return_time}")
            except TempHireBooking.DoesNotExist:
                print("TempHireBooking.DoesNotExist: Could not find TempHireBooking for session data.")
                messages.error(request, "Your temporary booking could not be found or has expired. Please select your hire dates.")
                if 'temp_booking_id' in request.session:
                    print("Deleting temp_booking_id from session.")
                    del request.session['temp_booking_id']
                if 'temp_booking_uuid' in request.session:
                    print("Deleting temp_booking_uuid from session.")
                    del request.session['temp_booking_uuid']
                # Continue with default values as if accessed directly
            except Exception as e:
                 print(f"An unexpected error occurred while retrieving TempHireBooking: {e}")
                 messages.error(request, "An unexpected error occurred while retrieving your temporary booking.")


        # If no temp_booking exists (direct access or expired), set default values
        # These will be used for the initial display and pre-filling the form.
        # They will *not* be saved to the database unless the Step 1 form is submitted.
        if not temp_booking or not (temp_booking.pickup_date and temp_booking.pickup_time and temp_booking.return_date and temp_booking.return_time):
            print("No valid TempHireBooking found. Using default dates/times.")
            # Set sensible defaults for initial view
            now = timezone.now()
            default_pickup_date = now.date()
            # Round to nearest 15 minutes for time options consistency
            default_pickup_time = now.time().replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
            # Ensure default return date is at least one day after pickup
            default_return_datetime = now + datetime.timedelta(days=1)
            default_return_date = default_return_datetime.date()
             # Round to nearest 15 minutes for time options consistency
            default_return_time = default_return_datetime.time().replace(minute=(default_return_datetime.minute // 15) * 15, second=0, microsecond=0)


            # Create a 'dummy' temp_booking object for consistent variable access
            # This is not saved to the DB at this point.
            temp_booking_display = TempHireBooking(
                pickup_date=default_pickup_date,
                pickup_time=default_pickup_time,
                return_date=default_return_date,
                return_time=default_return_time,
                has_motorcycle_license=True # Default to true for broader initial display
            )
            print(f"Using default dates/times for display: Pickup={default_pickup_date} {default_pickup_time}, Return={default_return_date} {default_return_time}")
            messages.info(request, "Please select your desired hire dates and times to view available motorcycles.")
        else:
            temp_booking_display = temp_booking # Use the actual temp_booking if it exists and is valid
            print(f"Using TempHireBooking data for display: Pickup={temp_booking_display.pickup_date} {temp_booking_display.pickup_time}, Return={temp_booking_display.return_date} {temp_booking_display.return_time}")


        # Use temp_booking_display for calculations and form pre-filling
        # Ensure times are timezone-aware for calculation if needed, though datetime.combine handles this if dates are date objects
        pickup_datetime = timezone.make_aware(datetime.datetime.combine(temp_booking_display.pickup_date, temp_booking_display.pickup_time))
        return_datetime = timezone.make_aware(datetime.datetime.combine(temp_booking_display.return_date, temp_booking_display.return_time))
        has_license = temp_booking_display.has_motorcycle_license

        print(f"Calculated pickup_datetime (aware): {pickup_datetime}")
        print(f"Calculated return_datetime (aware): {return_datetime}")
        print(f"Has license: {has_license}")

        # Duration for pricing (using potentially default dates/times)
        duration_days = calculate_hire_duration_days(pickup_datetime, return_datetime)
        print(f"Calculated hire duration (days): {duration_days}")


        # --- 2. Filter Motorcycles ---
        # Start with all eligible motorcycles as a QuerySet
        all_eligible_motorcycles = Motorcycle.objects.filter(conditions__name='hire', is_available=True)
        print(f"Initial eligible motorcycles count: {all_eligible_motorcycles.count()}")

        # If no license, filter by engine size, converting to int.
        # This will convert the QuerySet to a list.
        if not has_license:
            print("User does not have a license, filtering for engine_size <= 50.")
            temp_available_motorcycles = [] # Use a temporary list
            for motorcycle in all_eligible_motorcycles:
                try:
                    engine_size_int = int(motorcycle.engine_size)
                    if engine_size_int <= 50:
                        temp_available_motorcycles.append(motorcycle)
                except ValueError:
                    print(f"Warning: Could not convert engine_size '{motorcycle.engine_size}' to int for motorcycle {motorcycle.id}")
            available_motorcycles = temp_available_motorcycles
        else:
            # If license, all eligible motorcycles are available initially (as a list)
            available_motorcycles = list(all_eligible_motorcycles)
        print(f"Available motorcycles count after license filter (and int conversion): {len(available_motorcycles)}")


        # Find motorcycles booked during the selected period
        conflicting_bookings = HireBooking.objects.filter(
            Q(pickup_date__lt=return_datetime.date()) |
            (Q(pickup_date=return_datetime.date()) & Q(pickup_time__lte=return_datetime.time())),
            Q(return_date__gt=pickup_datetime.date()) |
            (Q(return_date=pickup_datetime.date()) & Q(return_time__gte=pickup_datetime.time())),
            status__in=['pending', 'confirmed', 'in_progress']
        )
        booked_motorcycle_ids = conflicting_bookings.values_list('motorcycle__id', flat=True)
        print(f"Found {conflicting_bookings.count()} conflicting HireBookings.")
        print(f"Booked motorcycle IDs: {list(booked_motorcycle_ids)}")

        # Exclude booked motorcycles from the available_motorcycles list
        # Since available_motorcycles is now guaranteed to be a list, we filter it in Python
        final_motorcycles_list = [
            m for m in available_motorcycles if m.id not in booked_motorcycle_ids
        ]
        print(f"Final available motorcycles count after excluding booked: {len(final_motorcycles_list)}")


        # --- 3. Add Price Calculations and Other Annotations ---
        hire_settings = HireSettings.objects.first()
        if hire_settings:
            print(f"Hire Settings found. Default daily rate: {hire_settings.default_daily_rate}, Monthly discount: {hire_settings.monthly_discount_percentage}%")
        else:
            print("No Hire Settings found.")


        motorcycles_with_prices = []
        for motorcycle in final_motorcycles_list: # Iterate over the final list
             base_daily_rate = motorcycle.daily_hire_rate or (hire_settings.default_daily_rate if hire_settings else 0)
             monthly_discount_factor = hire_settings.monthly_discount_percentage / 100 if hire_settings and hire_settings.monthly_discount_percentage is not None else 0
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
             print(f"Calculated price for {motorcycle.brand} {motorcycle.model}: Daily Display Rate=${discounted_daily_rate_for_display:.2f}, Total Price=${total_hire_price_for_bike:.2f}")


        # --- 4. Sorting ---
        order_by = request.GET.get('order', 'price_low_to_high')
        print(f"Sorting by: {order_by}")
        if order_by == 'price_low_to_high':
             motorcycles_with_prices.sort(key=lambda x: x['total_hire_price'])
        elif order_by == 'price_high_to_low':
             motorcycles_with_prices.sort(key=lambda x: x['total_hire_price'], reverse=True)

        # --- 5. Pagination ---
        paginator = Paginator(motorcycles_with_prices, self.paginate_by)
        page_number = request.GET.get('page')

        print(f"Paginating. Total items: {len(motorcycles_with_prices)}, Items per page: {self.paginate_by}, Requested page: {page_number}")

        try:
            page_obj = paginator.page(page_number)
            print(f"Serving page {page_obj.number} of {paginator.num_pages}. Items on this page: {len(page_obj.object_list)}")
        except PageNotAnInteger:
            page_obj = paginator.page(1)
            print(f"Invalid page number, serving page 1 of {paginator.num_pages}. Items on this page: {len(page_obj.object_list)}")
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
            print(f"Empty page requested, serving last page ({page_obj.number} of {paginator.num_pages}). Items on this page: {len(page_obj.object_list)}")


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
                'pick_up_date': temp_booking_display.pickup_date.isoformat() if temp_booking_display.pickup_date else '',
                'pick_up_time': temp_booking_display.pickup_time.strftime('%H:%M') if temp_booking_display.pickup_time else '',
                'return_date': temp_booking_display.return_date.isoformat() if temp_booking_display.return_date else '',
                'return_time': temp_booking_display.return_time.strftime('%H:%M') if temp_booking_display.return_time else '',
                'has_motorcycle_license': 'true' if temp_booking_display.has_motorcycle_license else 'false',
            },
            'temp_booking': temp_booking, # This will be the actual DB object if it exists, otherwise None
        }

        print(f"Context original_inputs for form pre-fill: {context['original_inputs']}")
        print(f"Context temp_booking object: {temp_booking}") # Will print the object or None

        if not motorcycles_with_prices and temp_booking_display.pickup_date and temp_booking_display.return_date:
             context['no_bikes_message'] = (
                 f"No motorcycles found for hire from {temp_booking_display.pickup_date.strftime('%d %b %Y')} "
                 f"to {temp_booking_display.return_date.strftime('%d %b %Y')}."
             )
             print(f"No bikes found message: {context['no_bikes_message']}")

        print("Rendering template.")
        print("--- BikeChoiceView GET END ---")
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
     # This logic might need refinement depending on how you define a "hire day"
     # For instance, a 25-hour hire might be 2 days, but a 23-hour hire might be 1 day.
     # The current logic counts 23 hours across midnight as 2 days (1 day difference + 1).
     # If you need precise 24-hour blocks or specific business hour logic, adjust this.
     if duration.total_seconds() > 0 and days == 0:
         days = 1
     elif duration.total_seconds() > 0 and return_datetime.time() > pickup_datetime.time():
         days += 1
     return days