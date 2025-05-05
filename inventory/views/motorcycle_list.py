# inventory/views/motorcycle_list.py

from django.shortcuts import render, redirect
from django.views.generic import ListView
from django.db.models import Q
import datetime
from django.contrib import messages
from inventory.models import Motorcycle
from hire.models import HireBooking
from decimal import Decimal


# Base class for displaying lists of motorcycles
class MotorcycleListView(ListView):
    model = Motorcycle
    template_name = 'inventory/motorcycle_list.html'
    context_object_name = 'motorcycles'
    paginate_by = 12

    # Applies common GET parameters filters and sorting to a queryset
    def _apply_common_filters_and_sorting(self, queryset):
        brand = self.request.GET.get('brand')
        model_query = self.request.GET.get('model')
        year_min = self.request.GET.get('year_min')
        year_max = self.request.GET.get('year_max')
        price_min = self.request.GET.get('price_min')
        price_max = self.request.GET.get('price_max')

        if brand:
            # Corrected: Use iexact for case-insensitive brand filtering
            queryset = queryset.filter(brand__iexact=brand)
        if model_query:
            queryset = queryset.filter(model__icontains=model_query)
        try:
            if year_min: queryset = queryset.filter(year__gte=int(year_min))
            if year_max: queryset = queryset.filter(year__lte=int(year_max))
        except (ValueError, TypeError): pass

        try:
            # Use Decimal for price filtering
            if price_min:
                 queryset = queryset.filter(price__gte=Decimal(price_min))
            if price_max:
                 queryset = queryset.filter(price__lte=Decimal(price_max))
        # Catch potential errors from Decimal conversion as well
        except (ValueError, TypeError):
            pass

        order = self.request.GET.get('order', 'price_low_to_high')

        if order == 'price_low_to_high':
            # Handle None prices by ordering them last
            queryset = queryset.order_by('price')
        elif order == 'price_high_to_low':
            # Handle None prices by ordering them first
            queryset = queryset.order_by('-price')
        elif order == 'age_new_to_old':
            queryset = queryset.order_by('-year', '-pk')
        elif order == 'age_old_to_new':
            queryset = queryset.order_by('year', 'pk')
        else:
            queryset = queryset.order_by('price')

        return queryset

    # Builds the queryset based on filters and conditions
    def get_queryset(self):
        # Start with base queryset (available motorcycles) and apply condition filter
        # This is for the public-facing views (New, Used, Hire)
        queryset = super().get_queryset().filter(is_available=True)

        condition_name = getattr(self, 'condition_name', None) or self.kwargs.get('condition_name') or self.request.GET.get('condition')

        if condition_name:
            if condition_name.lower() == 'used':
                 queryset = queryset.filter(conditions__name__in=['used', 'demo']).distinct()
            elif condition_name.lower() in ['new', 'hire']:
                 queryset = queryset.filter(conditions__name__iexact=condition_name).distinct()

        # Apply common filters and sorting using the helper
        # Common filters (brand, model, year, price) are applied AFTER condition and availability for public views
        queryset = self._apply_common_filters_and_sorting(queryset)


        return queryset

    # Adds common context data like filters and sorting
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        condition_name = getattr(self, 'condition_name', None) or self.kwargs.get('condition_name') or self.request.GET.get('condition')

        if condition_name:
            context['condition'] = condition_name
            context['condition_lower'] = condition_name.lower()

        if hasattr(self, 'url_name'):
             context['current_url_name'] = self.url_name

        # Filter options context should reflect the base queryset before GET filters apply
        # i.e., available bikes, potentially filtered by condition_name attribute
        # This logic is for the public-facing views. AllMotorcycleListView will override this.
        filtered_for_options = Motorcycle.objects.filter(is_available=True)
        if condition_name: # Use the determined condition_name here
             if condition_name.lower() == 'used':
                  filtered_for_options = filtered_for_options.filter(conditions__name__in=['used', 'demo']).distinct()
             elif condition_name.lower() in ['new', 'hire']:
                 filtered_for_options = filtered_for_options.filter(conditions__name__iexact=condition_name).distinct()


        context['brands'] = sorted(list(filtered_for_options.values_list('brand', flat=True).distinct()))

        years = list(filtered_for_options.values_list('year', flat=True).distinct())
        if years:
            min_year = min(years)
            max_year = max(years)
            context['years'] = list(range(max_year, min_year - 1, -1))
        else:
            context['years'] = []

        context['request'] = self.request

        context['current_order'] = self.request.GET.get('order', 'price_low_to_high')

        return context

# Lists all motorcycles (available or not, for admin view)
class AllMotorcycleListView(MotorcycleListView):
    template_name = 'inventory/all.html'

    def get_queryset(self):
        # Start with ALL motorcycles, available or not, for the admin view
        queryset = Motorcycle.objects.all()

        # --- Add Availability Filtering ---
        availability_filter = self.request.GET.get('availability', 'all') # Default to 'all'

        if availability_filter == 'available':
            queryset = queryset.filter(is_available=True)
        elif availability_filter == 'unavailable':
            queryset = queryset.filter(is_available=False)
        # If 'all' or other value, no additional filtering on is_available is applied here

        # Apply common filters and sorting using the helper from the base class
        # Common filters (brand, model, year, price) are applied to ALL bikes here
        queryset = self._apply_common_filters_and_sorting(queryset)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Corrected: For the AllMotorcycleListView, filter options should include all bikes
        filtered_for_options = Motorcycle.objects.all()

        context['brands'] = sorted(list(filtered_for_options.values_list('brand', flat=True).distinct()))

        years = list(filtered_for_options.values_list('year', flat=True).distinct())
        if years:
            min_year = min(years)
            max_year = max(years)
            context['years'] = list(range(max_year, min_year - 1, -1))
        else:
            context['years'] = []

        # The 'condition' context variable might not be needed or should be handled differently
        # for the 'all' view if filtering by condition isn't the primary purpose.
        # Removing or adjusting the condition-related context if necessary for this view.
        context.pop('condition', None)
        context.pop('condition_lower', None)

        # --- Add availability filter to context ---
        context['current_availability_filter'] = self.request.GET.get('availability', 'all')


        return context


    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            # Optionally add a message here before redirecting
            # messages.warning(request, "You do not have permission to access this page.")
            return redirect('core:index')
        return super().dispatch(request, *args, **kwargs)


# Lists new motorcycles
class NewMotorcycleListView(MotorcycleListView):
    template_name = 'inventory/new.html'
    condition_name = 'new'
    url_name = 'inventory:new'


# Lists used and demo motorcycles
class UsedMotorcycleListView(MotorcycleListView):
    template_name = 'inventory/used.html'
    condition_name = 'used'
    url_name = 'inventory:used'


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