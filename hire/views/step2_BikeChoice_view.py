import datetime
from django.shortcuts import render
from django.views import View
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone

from inventory.models import Motorcycle
from dashboard.models import HireSettings, BlockedHireDate
from hire.models import TempHireBooking
from ..hire_pricing import calculate_motorcycle_hire_price


class BikeChoiceView(View):
    template_name = 'hire/step2_choose_bike.html'
    paginate_by = 9

    def get(self, request, *args, **kwargs):
        abandonment_threshold = timezone.now() - datetime.timedelta(hours=2)

        abandoned_bookings = TempHireBooking.objects.filter(updated_at__lt=abandonment_threshold)

        if abandoned_bookings.exists():
            count = abandoned_bookings.count()
            abandoned_bookings.delete()

        hire_settings = HireSettings.objects.first()

        temp_booking_id = request.session.get('temp_booking_id') or request.GET.get('temp_booking_id')
        temp_booking_uuid = request.session.get('temp_booking_uuid') or request.GET.get('temp_booking_uuid')

        temp_booking = None
        if temp_booking_id and temp_booking_uuid:
            try:
                temp_booking = TempHireBooking.objects.get(id=temp_booking_id, session_uuid=temp_booking_uuid)
                request.session['temp_booking_id'] = temp_booking.id
                request.session['temp_booking_uuid'] = str(temp_booking.session_uuid)
            except TempHireBooking.DoesNotExist:
                messages.error(request, "Your previous booking details could not be found. Please re-enter your dates.")
                if 'temp_booking_id' in request.session:
                    del request.session['temp_booking_id']
                if 'temp_booking_uuid' in request.session:
                    del request.session['temp_booking_uuid']
                temp_booking = None

        if not temp_booking:
            messages.info(request, "Please select your pickup and return dates to find available motorcycles.")
            context = {
                'hire_settings': hire_settings,
                'motorcycles': [],
                'is_paginated': False,
                'temp_booking': None,
            }
            return render(request, self.template_name, context)

        pickup_date = temp_booking.pickup_date
        pickup_time = temp_booking.pickup_time
        return_date = temp_booking.return_date
        return_time = temp_booking.return_time
        has_motorcycle_license = temp_booking.has_motorcycle_license

        if not all([pickup_date, pickup_time, return_date, return_time]):
            messages.error(request, "Please provide valid pickup and return dates and times.")
            if 'temp_booking_id' in request.session:
                del request.session['temp_booking_id']
            if 'temp_booking_uuid' in request.session:
                del request.session['temp_booking_uuid']
            temp_booking = None
            context = {
                'hire_settings': hire_settings,
                'motorcycles': [],
                'is_paginated': False,
                'temp_booking': None,
            }
            return render(request, self.template_name, context)


        pickup_datetime = timezone.make_aware(datetime.datetime.combine(pickup_date, pickup_time))
        return_datetime = timezone.make_aware(datetime.datetime.combine(return_date, return_time))

        available_motorcycles = Motorcycle.objects.filter(
            is_available=True
        ).exclude(
            Q(hire_bookings__pickup_date__lt=return_date, hire_bookings__return_date__gt=pickup_date)
        )

        if not has_motorcycle_license:
            available_motorcycles = available_motorcycles.filter(
                engine_size__lte=50
            )
        else:
            pass

        motorcycles_with_prices = []
        for motorcycle in available_motorcycles:
            total_hire_price = calculate_motorcycle_hire_price(
                motorcycle=motorcycle,
                pickup_date=pickup_date,
                return_date=return_date,
                pickup_time=pickup_time,
                return_time=return_time,
                hire_settings=hire_settings
            )

            daily_hire_rate_display = motorcycle.daily_hire_rate if motorcycle.daily_hire_rate is not None else hire_settings.default_daily_rate


            motorcycles_with_prices.append({
                'object': motorcycle,
                'daily_hire_rate_display': daily_hire_rate_display,
                'total_hire_price': total_hire_price,
            })

        order_by = request.GET.get('order', 'price_low_to_high')
        if order_by == 'price_low_to_high':
            motorcycles_with_prices.sort(key=lambda x: x['total_hire_price'])
        elif order_by == 'price_high_to_low':
            motorcycles_with_prices.sort(key=lambda x: x['total_hire_price'], reverse=True)

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
