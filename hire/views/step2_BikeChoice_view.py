import datetime
from django.shortcuts import render, redirect
from django.views import View
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

from inventory.models import Motorcycle
from ..models import TempHireBooking, HireBooking
from dashboard.models import HireSettings, BlockedHireDate
from ..views.utils import calculate_hire_price, calculate_hire_duration_days


class BikeChoiceView(View):
    template_name = 'hire/step2_choose_bike.html'
    paginate_by = 9

    def get(self, request, *args, **kwargs):
        temp_booking_id = request.session.get('temp_booking_id')
        temp_booking_uuid = request.session.get('temp_booking_uuid')
        temp_booking = None

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
            except Exception as e:
                messages.error(request, "An unexpected error occurred while retrieving your temporary booking.")

        if not temp_booking or not (temp_booking.pickup_date and temp_booking.pickup_time and temp_booking.return_date and temp_booking.return_time):
            now = timezone.now()
            default_pickup_date = now.date()
            default_pickup_time = now.time().replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
            default_return_datetime = now + datetime.timedelta(days=1)
            default_return_date = default_return_datetime.date()
            default_return_time = default_return_datetime.time().replace(minute=(default_return_datetime.minute // 15) * 15, second=0, microsecond=0)

            temp_booking_display = TempHireBooking(
                pickup_date=default_pickup_date,
                pickup_time=default_pickup_time,
                return_date=default_return_date,
                return_time=default_return_time,
                has_motorcycle_license=True
            )
            messages.info(request, "Please select your desired hire dates and times to view available motorcycles.")
        else:
            temp_booking_display = temp_booking

        pickup_datetime = timezone.make_aware(datetime.datetime.combine(temp_booking_display.pickup_date, temp_booking_display.pickup_time))
        return_datetime = timezone.make_aware(datetime.datetime.combine(temp_booking_display.return_date, temp_booking_display.return_time))
        has_license = temp_booking_display.has_motorcycle_license

        hire_duration_days = calculate_hire_duration_days(
                temp_booking_display.pickup_date, temp_booking_display.return_date, temp_booking_display.pickup_time, temp_booking_display.return_time
            )

        all_eligible_motorcycles = Motorcycle.objects.filter(conditions__name='hire', is_available=True)

        if not has_license:
            temp_available_motorcycles = []
            for motorcycle in all_eligible_motorcycles:
                try:
                    engine_size_int = int(motorcycle.engine_size)
                    if engine_size_int <= 50:
                        temp_available_motorcycles.append(motorcycle)
                except ValueError:
                    pass
            available_motorcycles = temp_available_motorcycles
        else:
            available_motorcycles = list(all_eligible_motorcycles)

        conflicting_bookings = HireBooking.objects.filter(
            Q(pickup_date__lt=return_datetime.date()) |
            (Q(pickup_date=return_datetime.date()) & Q(pickup_time__lte=return_datetime.time())),
            Q(return_date__gt=pickup_datetime.date()) |
            (Q(return_date=pickup_datetime.date()) & Q(return_time__gte=pickup_datetime.time())),
            status__in=['pending', 'confirmed', 'in_progress']
        )
        booked_motorcycle_ids = conflicting_bookings.values_list('motorcycle__id', flat=True)

        final_motorcycles_list = [
            m for m in available_motorcycles if m.id not in booked_motorcycle_ids
        ]

        hire_settings = HireSettings.objects.first()

        motorcycles_with_prices = []
        for motorcycle in final_motorcycles_list:
            base_daily_rate = motorcycle.daily_hire_rate or (hire_settings.default_daily_rate if hire_settings else 0)
            monthly_discount_factor = hire_settings.monthly_discount_percentage / 100 if hire_settings and hire_settings.monthly_discount_percentage is not None else 0
            discounted_daily_rate_for_display = base_daily_rate * (1 - monthly_discount_factor)

            total_hire_price_for_bike = calculate_hire_price(
                    motorcycle,
                    hire_duration_days,
                    hire_settings
               )

            motorcycles_with_prices.append({
                    'object': motorcycle,
                    'daily_hire_rate_display': discounted_daily_rate_for_display,
                    'total_hire_price': total_hire_price_for_bike,
               })

        order_by = request.GET.get('order', 'price_low_to_high')
        if order_by == 'price_low_to_high':
            motorcycles_with_prices.sort(key=lambda x: x['total_hire_price'])
        elif order_by == 'price_high_to_low':
            motorcycles_with_prices.sort(key=lambda x: x['total_hire_price'], reverse=True)

        paginator = Paginator(motorcycles_with_prices, self.paginate_by)
        page_number = request.GET.get('page')

        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        context = {
            'motorcycles': page_obj.object_list,
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages(),
            'paginator': paginator,
            'current_order': order_by,
            'hire_settings': hire_settings,
            'hire_start_date': temp_booking_display.pickup_date,
            'hire_end_date': temp_booking_display.return_date,
            'original_inputs': {
                'pick_up_date': temp_booking_display.pickup_date.isoformat() if temp_booking_display.pickup_date else '',
                'pick_up_time': temp_booking_display.pickup_time.strftime('%H:%M') if temp_booking_display.pickup_time else '',
                'return_date': temp_booking_display.return_date.isoformat() if temp_booking_display.return_date else '',
                'return_time': temp_booking_display.return_time.strftime('%H:%M') if temp_booking_display.return_time else '',
                'has_motorcycle_license': 'true' if temp_booking_display.has_motorcycle_license else 'false',
            },
            'temp_booking': temp_booking,
        }

        if not motorcycles_with_prices and temp_booking_display.pickup_date and temp_booking_display.return_date:
            context['no_bikes_message'] = (
                f"No motorcycles found for hire from {temp_booking_display.pickup_date.strftime('%d %b %Y')} "
                f"to {temp_booking_display.return_date.strftime('%d %b %Y')}."
            )

        return render(request, self.template_name, context)