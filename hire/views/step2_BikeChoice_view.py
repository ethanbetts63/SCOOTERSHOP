import datetime
from django.shortcuts import render
from django.views import View
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone

from inventory.models import Motorcycle
from dashboard.models import HireSettings, BlockedHireDate
from hire.models import TempHireBooking # Import TempHireBooking model

class BikeChoiceView(View):
    """
    Displays a list of motorcycles available for hire based on selected dates and license status.
    Allows users to select a motorcycle to proceed to the next booking step.
    """
    template_name = 'hire/step2_choose_bike.html'
    paginate_by = 9 # Number of motorcycles per page

    def get(self, request, *args, **kwargs):
        # Retrieve hire settings
        hire_settings = HireSettings.objects.first()

        # Try to get TempHireBooking from session or URL parameters
        temp_booking_id = request.session.get('temp_booking_id') or request.GET.get('temp_booking_id')
        temp_booking_uuid = request.session.get('temp_booking_uuid') or request.GET.get('temp_booking_uuid')
        
        print(f"--- Debugging BikeChoiceView.get ---")
        print(f"temp_booking_id from session/GET: {temp_booking_id}")
        print(f"temp_booking_uuid from session/GET: {temp_booking_uuid}")

        temp_booking = None
        if temp_booking_id and temp_booking_uuid:
            try:
                temp_booking = TempHireBooking.objects.get(id=temp_booking_id, session_uuid=temp_booking_uuid)
                # Update session if retrieved from URL (e.g., first time landing on step 2 via direct link)
                request.session['temp_booking_id'] = temp_booking.id
                request.session['temp_booking_uuid'] = str(temp_booking.session_uuid)
                print(f"TempHireBooking retrieved successfully: {temp_booking.id}")
            except TempHireBooking.DoesNotExist:
                messages.error(request, "Your previous booking details could not be found. Please re-enter your dates.")
                # Clear session if invalid temp_booking_id/uuid
                if 'temp_booking_id' in request.session:
                    del request.session['temp_booking_id']
                if 'temp_booking_uuid' in request.session:
                    del request.session['temp_booking_uuid']
                temp_booking = None # Ensure temp_booking is None
                print(f"TempHireBooking.DoesNotExist: Clearing session keys.")

        # If no temporary booking exists, redirect to home or step 1 to start fresh
        if not temp_booking:
            messages.info(request, "Please select your pickup and return dates to find available motorcycles.")
            print(f"No TempHireBooking found. Rendering without motorcycles.")
            context = {
                'hire_settings': hire_settings,
                'motorcycles': [], # No motorcycles to show without dates
                'is_paginated': False,
                'temp_booking': None, # Ensure temp_booking is None in context
            }
            return render(request, self.template_name, context)

        # Retrieve dates and license status from the TempHireBooking instance
        pickup_date = temp_booking.pickup_date
        pickup_time = temp_booking.pickup_time
        return_date = temp_booking.return_date
        return_time = temp_booking.return_time
        has_motorcycle_license = temp_booking.has_motorcycle_license # This is the key variable from Step 1

        print(f"has_motorcycle_license from TempHireBooking: {has_motorcycle_license}")

        # If any date/time is missing in temp_booking (e.g., direct access without step 1), redirect
        if not all([pickup_date, pickup_time, return_date, return_time]):
            messages.error(request, "Please provide valid pickup and return dates and times.")
            # Clear session keys if data is incomplete
            if 'temp_booking_id' in request.session:
                del request.session['temp_booking_id']
            if 'temp_booking_uuid' in request.session:
                del request.session['temp_booking_uuid']
            temp_booking = None # Ensure temp_booking is None in context
            print(f"Missing pickup/return dates/times in TempHireBooking. Clearing session.")
            context = {
                'hire_settings': hire_settings,
                'motorcycles': [],
                'is_paginated': False,
                'temp_booking': None,
            }
            return render(request, self.template_name, context)


        pickup_datetime = timezone.make_aware(datetime.datetime.combine(pickup_date, pickup_time))
        return_datetime = timezone.make_aware(datetime.datetime.combine(return_date, return_time))
        
        # Recalculate duration in days for display and price calculation
        duration = (return_datetime - pickup_datetime).days + (1 if (return_datetime - pickup_datetime).seconds > 0 else 0)
        if duration == 0: # Minimum 1 day hire if pickup and return are same day but different times
            duration = 1

        # Determine available motorcycles based on license and existing bookings
        available_motorcycles = Motorcycle.objects.filter(
            is_available=True
        ).exclude(
            # Exclude motorcycles that are already booked for any part of the requested period
            Q(hire_bookings__pickup_date__lt=return_date, hire_bookings__return_date__gt=pickup_date) |
            Q(temp_hire_bookings__pickup_date__lt=return_date, temp_hire_bookings__return_date__gt=pickup_date)
        )
        print(f"Motorcycles available before license filter (count): {available_motorcycles.count()}")
        print(f"Motorcycles available before license filter (IDs): {[m.id for m in available_motorcycles]}")


        # --- IMPORTANT: Filter motorcycles based on license requirement ---
        # As per Australian law, motorcycles with engine size > 50cc require a motorcycle license.
        # If the user does NOT have a motorcycle license, only show bikes with engine_size <= 50cc.
        if not has_motorcycle_license:
            print(f"User does NOT have a motorcycle license. Filtering for engine_size <= 50.")
            available_motorcycles = available_motorcycles.filter(
                engine_size__lte=50
            )
        else:
            print(f"User HAS a motorcycle license. All engine sizes are considered.")
        
        print(f"Motorcycles available AFTER license filter (count): {available_motorcycles.count()}")
        print(f"Motorcycles available AFTER license filter (IDs): {[m.id for m in available_motorcycles]}")
        print(f"Motorcycles available AFTER license filter (Engine Sizes): {[m.engine_size for m in available_motorcycles]}")


        # Annotate motorcycles with calculated hire rates and total price
        motorcycles_with_prices = []
        for motorcycle in available_motorcycles:
            # Calculate daily hire rate (you might have more complex logic here)
            daily_hire_rate = motorcycle.daily_hire_rate
            
            # Calculate total hire price for the period
            total_hire_price = daily_hire_rate * duration

            motorcycles_with_prices.append({
                'object': motorcycle,
                'daily_hire_rate_display': daily_hire_rate,
                'total_hire_price': total_hire_price,
            })

        # Sorting logic
        order_by = request.GET.get('order', 'price_low_to_high')
        if order_by == 'price_low_to_high':
            motorcycles_with_prices.sort(key=lambda x: x['total_hire_price'])
        elif order_by == 'price_high_to_low':
            motorcycles_with_prices.sort(key=lambda x: x['total_hire_price'], reverse=True)

        # Pagination
        paginator = Paginator(motorcycles_with_prices, self.paginate_by)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'motorcycles': page_obj,
            'is_paginated': page_obj.has_other_pages(),
            'page_obj': page_obj,
            'paginator': paginator,
            'current_order': order_by,
            'hire_settings': hire_settings,
            'temp_booking': temp_booking,
            'blocked_hire_dates': BlockedHireDate 
        }
        return render(request, self.template_name, context)

