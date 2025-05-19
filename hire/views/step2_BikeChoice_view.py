# hire/views/step2_BikeChoice_view.py

from django.shortcuts import render, redirect
from django.views import View # Inherit from Django's base View
from django.db.models import Q, Min, Max, Case, When, Value, DecimalField
import datetime
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from hire.models import HireBooking
from dashboard.models import HireSettings
from inventory.models import Motorcycle
from dashboard.models import BlockedHireDate
import logging
from decimal import Decimal
import math
import json

class BikeChoiceView(View):
    template_name = 'hire/step2_choose_bike.html'
    url_name = 'hire:step2_choose_bike'
    paginate_by = 12 # Manually add pagination attribute

    def get(self, request, *args, **kwargs):
        # This is the GET request to display the bikes
        # We need to get booking data from the session
        pick_up_datetime_iso = request.session.get('booking_pickup_datetime')
        return_datetime_iso = request.session.get('booking_return_datetime')
        has_motorcycle_license = request.session.get('booking_has_motorcycle_license', False)

        self.pick_up_datetime = None
        self.return_datetime = None
        self.duration_days = None
        self.original_inputs = {}

        hire_settings = None
        try:
            hire_settings = HireSettings.objects.first()
            if not hire_settings:
                messages.error(request, "Hire settings are not configured. Availability and pricing may be inaccurate.")
        except Exception:
            messages.error(request, "Could not load hire settings. Availability and pricing may be inaccurate.")
            pass

        # --- Retrieve and validate session data ---
        if pick_up_datetime_iso and return_datetime_iso:
            try:
                self.pick_up_datetime = timezone.datetime.fromisoformat(pick_up_datetime_iso)
                self.return_datetime = timezone.datetime.fromisoformat(return_datetime_iso)

                if timezone.is_naive(self.pick_up_datetime):
                    self.pick_up_datetime = timezone.make_aware(self.pick_up_datetime)
                if timezone.is_naive(self.return_datetime):
                    self.return_datetime = timezone.make_aware(self.return_datetime)

                if self.return_datetime <= self.pick_up_datetime:
                    messages.error(request, "Invalid hire dates in session. Please select dates again.")
                    request.session.pop('booking_pickup_datetime', None)
                    request.session.pop('booking_return_datetime', None)
                    request.session.pop('booking_has_motorcycle_license', None)
                    return redirect('hire:step1_select_datetime')

                duration = self.return_datetime - self.pick_up_datetime
                self.duration_days = duration.total_seconds() / 3600 / 24

                errors = []
                if hire_settings:
                    if hire_settings.minimum_hire_duration_days is not None and self.duration_days < hire_settings.minimum_hire_duration_days:
                        errors.append(f"Minimum hire duration is {hire_settings.minimum_hire_duration_days} days.")
                    if hire_settings.maximum_hire_duration_days is not None and self.duration_days > hire_settings.maximum_hire_duration_days:
                         errors.append(f"Maximum hire duration is {hire_settings.maximum_hire_duration_days} days.")

                    if hire_settings.booking_lead_time_hours is not None:
                         now = timezone.now()
                         min_pickup_time = now + timedelta(hours=hire_settings.booking_lead_time_hours)
                         if self.pick_up_datetime < min_pickup_time:
                              errors.append(f"Pickup must be at least {hire_settings.booking_lead_time_hours} hours from now.")

                blocked_dates = BlockedHireDate.objects.all()
                for blocked in blocked_dates:
                     blocked_start_datetime = timezone.make_aware(datetime.datetime.combine(blocked.start_date, datetime.time.min))
                     blocked_end_datetime = timezone.make_aware(datetime.datetime.combine(blocked.end_date, datetime.time.max))

                     if (self.pick_up_datetime <= blocked_end_datetime) and (self.return_datetime >= blocked_start_datetime):
                          errors.append(f"Your selected hire period conflicts with a blocked period ({blocked.start_date} to {blocked.end_date}).")
                          break

                if errors:
                    for error in errors:
                        messages.error(request, error)
                    request.session.pop('booking_pickup_datetime', None)
                    request.session.pop('booking_return_datetime', None)
                    request.session.pop('booking_has_motorcycle_license', None)
                    return redirect('hire:step1_select_datetime')

                self.original_inputs = {
                    'pick_up_date': self.pick_up_datetime.strftime('%Y-%m-%d'),
                    'pick_up_time': self.pick_up_datetime.strftime('%H:%M'),
                    'return_date': self.return_datetime.strftime('%Y-%m-%d'),
                    'return_time': self.return_datetime.strftime('%H:%M'),
                    'has_motorcycle_license': str(has_motorcycle_license).lower()
                }


            except ValueError:
                messages.error(request, "Error parsing hire dates from session. Please select dates again.")
                request.session.pop('booking_pickup_datetime', None)
                request.session.pop('booking_return_datetime', None)
                request.session.pop('booking_has_motorcycle_license', None)
                return redirect('hire:step1_select_datetime')
            except Exception as e:
                messages.error(request, f"An unexpected error occurred processing hire dates: {e}")
                request.session.pop('booking_pickup_datetime', None)
                request.session.pop('booking_return_datetime', None)
                request.session.pop('booking_has_motorcycle_license', None)
                return redirect('hire:step1_select_datetime')

        else:
            messages.info(request, "Please select your desired hire dates and times.")

        # --- Build the queryset based on session data ---
        queryset = Motorcycle.objects.filter(
            is_available=True,
            conditions__name='hire'
        )

        if self.pick_up_datetime and self.return_datetime:
            # Exclude motorcycles with conflicting confirmed/pending bookings (using corrected logic)
            ends_before_or_at_desired_pickup = (
                Q(return_date__lt=self.pick_up_datetime.date()) |
                Q(return_date=self.pick_up_datetime.date(), return_time__lte=self.pick_up_datetime.time())
            )

            starts_after_or_at_desired_return = (
                Q(pickup_date__gt=self.return_datetime.date()) |
                Q(pickup_date=self.return_datetime.date(), pickup_time__gte=self.return_datetime.time())
            )

            no_overlap = ends_before_or_at_desired_pickup | starts_after_or_at_desired_return

            conflicting_bookings = HireBooking.objects.filter(
                status__in=['confirmed', 'pending'],
                motorcycle__in=queryset,
            ).exclude(no_overlap).values_list('motorcycle_id', flat=True)

            queryset = queryset.exclude(id__in=conflicting_bookings)

            # --- CORRECTED: Filter by license status based on engine size ---
            # If user does NOT have a motorcycle license, only show bikes <= 50cc
            if not has_motorcycle_license:
                 queryset = queryset.filter(engine_size__lte=50)


        else:
            queryset = Motorcycle.objects.none()


        # --- Apply sorting (keep existing sorting based on GET params) ---
        order = self.request.GET.get('order', 'price_low_to_high')

        if hire_settings and hire_settings.default_daily_rate is not None:
             queryset = queryset.annotate(
                 effective_daily_rate=Case(
                     When(daily_hire_rate__isnull=False, then='daily_hire_rate'),
                     default=hire_settings.default_daily_rate,
                     output_field=DecimalField()
                 )
             )

        if order == 'price_low_to_high':
            queryset = queryset.order_by('effective_daily_rate' if 'effective_daily_rate' in queryset.query.annotations else 'daily_hire_rate')
        elif order == 'price_high_to_low':
             queryset = queryset.order_by('-effective_daily_rate' if 'effective_daily_rate' in queryset.query.annotations else '-daily_hire_rate')
        elif order == 'age_new_to_old':
            queryset = queryset.order_by('-year', '-pk')
        elif order == 'age_old_to_new':
            queryset = queryset.order_by('year', 'pk')
        else:
            queryset = queryset.order_by('effective_daily_rate' if 'effective_daily_rate' in queryset.query.annotations else 'daily_hire_rate')


        # --- Pagination ---
        page = self.request.GET.get('page', 1)
        from django.core.paginator import Paginator
        paginator = Paginator(queryset, self.paginate_by)
        try:
            motorcycles_page = paginator.page(page)
        except Exception:
             if int(page) > paginator.num_pages:
                 motorcycles_page = paginator.page(paginator.num_pages)
             else:
                motorcycles_page = paginator.page(1)


        self.motorcycles_list = motorcycles_page.object_list
        self.page_obj = motorcycles_page
        self.is_paginated = paginator.num_pages > 1
        self.paginator = paginator


        return render(request, self.template_name, self.get_context_data())

    def get_context_data(self, **kwargs):
        context = {}
        context['motorcycles'] = self.motorcycles_list
        context['page_obj'] = self.page_obj
        context['is_paginated'] = self.is_paginated
        context['paginator'] = self.paginator

        context['original_inputs'] = self.original_inputs

        if self.pick_up_datetime and self.return_datetime and self.duration_days is not None:
             context['pick_up_date'] = self.pick_up_datetime.strftime('%Y-%m-%d')
             context['pick_up_time'] = self.pick_up_datetime.strftime('%H:%M')
             context['return_date'] = self.return_datetime.strftime('%Y-%m-%d')
             context['return_time'] = self.return_datetime.strftime('%H:%M')
             context['hire_days'] = math.ceil(self.duration_days) if self.duration_days is not None else None
             context['hire_start_date'] = self.pick_up_datetime.date().strftime('%Y-%m-%d')
             context['hire_end_date'] = self.return_datetime.date().strftime('%Y-%m-%d')

             hire_settings = context.get('hire_settings')
             if hire_settings:
                 updated_motorcycles_list = []
                 for motorcycle in self.motorcycles_list:
                     base_daily_rate = motorcycle.daily_hire_rate
                     if base_daily_rate is None and hire_settings.default_daily_rate is not None:
                         base_daily_rate = hire_settings.default_daily_rate

                     if base_daily_rate is not None:
                         if hire_settings.monthly_discount_percentage is not None and hire_settings.monthly_discount_percentage > 0:
                             monthly_discount_factor = (Decimal(100) - hire_settings.monthly_discount_percentage) / Decimal(100)
                             discounted_daily_rate = base_daily_rate * monthly_discount_factor
                             if self.duration_days is not None:
                                 motorcycle.total_hire_price = discounted_daily_rate * Decimal(str(self.duration_days))
                                 motorcycle.total_hire_price = motorcycle.total_hire_price.quantize(Decimal('0.01'))
                             motorcycle.display_daily_rate = discounted_daily_rate.quantize(Decimal('0.01'))
                         else:
                             if self.duration_days is not None:
                                 motorcycle.total_hire_price = base_daily_rate * Decimal(str(self.duration_days))
                                 motorcycle.total_hire_price = motorcycle.total_hire_price.quantize(Decimal('0.01'))
                             motorcycle.display_daily_rate = base_daily_rate.quantize(Decimal('0.01'))
                     else:
                         motorcycle.display_daily_rate = None
                         motorcycle.total_hire_price = None

                     updated_motorcycles_list.append(motorcycle)
                 context['motorcycles'] = updated_motorcycles_list
                 context['page_obj'].object_list = updated_motorcycles_list


        else:
             context['pick_up_date'] = ''
             context['pick_up_time'] = ''
             context['return_date'] = ''
             context['return_time'] = ''
             context['hire_days'] = None
             context['hire_start_date'] = None
             context['hire_end_date'] = None

             for motorcycle in self.motorcycles_list:
                 motorcycle.display_daily_rate = None
                 motorcycle.total_hire_price = None

        blocked_hire_dates = BlockedHireDate.objects.all()
        blocked_hire_date_ranges = []
        for blocked in blocked_hire_dates:
             blocked_hire_date_ranges.append({
                 'from': blocked.start_date.strftime('%Y-%m-%d'),
                 'to': blocked.end_date.strftime('%Y-%m-%d')
             })
        context['blocked_hire_date_ranges_json'] = json.dumps(blocked_hire_date_ranges)

        # --- CORRECTED: Use self.request.session ---
        context['has_motorcycle_license'] = self.request.session.get('booking_has_motorcycle_license', False)

        try:
            hire_settings = HireSettings.objects.first()
            context['hire_settings'] = hire_settings
        except Exception as e:
             logging.error(f"Error loading hire settings for context: {e}")

        context['current_order'] = self.request.GET.get('order', 'price_low_to_high')

        return context

    def post(self, request, *args, **kwargs):
        query_string = request.META.get('QUERY_STRING', '')
        redirect_url = redirect('hire:step1_select_datetime').url
        if query_string:
            redirect_url = f"{redirect_url}?{query_string}"
        return redirect(redirect_url)