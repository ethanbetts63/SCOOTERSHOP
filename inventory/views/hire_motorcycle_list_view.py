# inventory/views/hire_motorcycle_list_view.py

from django.db.models import Q
import datetime
from django.contrib import messages
from hire.models import HireBooking # Assuming HireBooking is in hire.models
from .motorcycle_list_view import MotorcycleListView # Import the base class


# Lists motorcycles available for hire
class HireMotorcycleListView(MotorcycleListView):
    template_name = 'inventory/hire.html'
    condition_name = 'hire'
    url_name = 'inventory:hire'

    # Adds hire-specific filtering (daily rate, date availability)
    def get_queryset(self):
        # Start by getting the base queryset (which applies is_available=True and condition_name='hire')
        # Then apply common filters and sorting
        queryset = super().get_queryset()
        # Note: Common filters (like price range) are less relevant for hire bikes based on the model
        # but the _apply_common_filters_and_sorting method is still called.
        # If price filtering should *not* apply to hire bikes, you would override
        # _apply_common_filters_and_sorting specifically in this class or adjust the base method.
        # For now, keeping the base method call.

        # Now apply hire-specific filters (daily rate and date availability)
        daily_rate_min = self.request.GET.get('daily_rate_min')
        daily_rate_max = self.request.GET.get('daily_rate_max')

        try:
            if daily_rate_min:
                queryset = queryset.filter(daily_hire_rate__gte=float(daily_rate_min))
            if daily_rate_max:
                queryset = queryset.filter(daily_hire_rate__lte=float(daily_rate_max))
        except (ValueError, TypeError):
            pass

        self.date_range = None

        hire_start_date_str = self.request.GET.get('hire_start_date')
        hire_end_date_str = self.request.GET.get('hire_end_date')

        if hire_start_date_str and hire_end_date_str:
            try:
                start_date = datetime.datetime.strptime(hire_start_date_str, '%Y-%m-%d').date()
                end_date = datetime.datetime.strptime(hire_end_date_str, '%Y-%m-%d').date()

                if start_date > end_date:
                    messages.error(self.request, "Hire start date cannot be after the end date.")
                    return self.model.objects.none()

                self.date_range = (start_date, end_date, hire_start_date_str, hire_end_date_str)

                # Find motorcycles booked within the date range
                conflicting_bookings = HireBooking.objects.filter(
                    status__in=['confirmed', 'pending'],
                    # Only consider bookings for motorcycles that are currently in our filtered queryset
                    motorcycle__in=queryset,
                ).filter(
                    # Check for overlapping date ranges
                    Q(pickup_datetime__date__lte=end_date, dropoff_datetime__date__gte=start_date)
                ).values_list('motorcycle_id', flat=True) # Get the IDs of conflicting motorcycles

                # Exclude motorcycles with conflicting bookings from the queryset
                queryset = queryset.exclude(id__in=conflicting_bookings)

            except ValueError:
                messages.error(self.request, "Invalid date format. Please use YYYY-MM-DD.")
                return self.model.objects.none()
            except Exception as e:
                messages.error(self.request, f"An error occurred while filtering by date: {e}")
                return self.model.objects.none()

        return queryset

    # Adds hire-specific context data (date range, hire days)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.date_range:
            start_date, end_date, hire_start_date_str, hire_end_date_str = self.date_range
            context['hire_start_date'] = hire_start_date_str
            context['hire_end_date'] = hire_end_date_str

            delta = end_date - start_date
            # Calculate the number of days inclusive of start and end dates
            context['hire_days'] = delta.days + 1
        else:
            context['hire_start_date'] = ''
            context['hire_end_date'] = ''
            context['hire_days'] = None

        return context