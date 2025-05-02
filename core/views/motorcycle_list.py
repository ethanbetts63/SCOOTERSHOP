# core/views/motorcycle_list.py

from django.shortcuts import render
from django.views.generic import ListView
from django.db.models import Q
import datetime
from ..models import Motorcycle, MotorcycleCondition, HireBooking # Import models
from .utils import get_featured_motorcycles # Import utility function


class MotorcycleListView(ListView):
    model = Motorcycle
    # This default template_name might not be used directly if subclasses override it
    # but it's fine to keep as a fallback or for a potential base list view.
    template_name = 'motorcycles/motorcycle_list.html'
    context_object_name = 'motorcycles'
    paginate_by = 12

    def get_queryset(self):
        # Start with base queryset (available motorcycles)
        queryset = super().get_queryset().filter(is_available=True)

        # Apply condition filter if specified in view kwargs
        # Note: We are relying on the 'condition_name' kwarg being set by the calling views (new, used, hire)
        condition_name = self.kwargs.get('condition_name')

        if condition_name:
            # Use the new conditions ManyToManyField
            if condition_name == 'used':
                 # Filter for motorcycles that have 'used' OR 'demo' in their conditions
                 queryset = queryset.filter(conditions__name__in=['used', 'demo']).distinct()
            else:
                 # Filter for motorcycles that have the specific condition
                 queryset = queryset.filter(conditions__name=condition_name).distinct()


        # --- Apply other filters ---
        brand = self.request.GET.get('brand')
        model_query = self.request.GET.get('model')
        year_min = self.request.GET.get('year_min')
        year_max = self.request.GET.get('year_max')
        price_min = self.request.GET.get('price_min')
        price_max = self.request.GET.get('price_max')

        if brand:
            queryset = queryset.filter(brand__icontains=brand) # Use icontains for case-insensitive
        if model_query:
            queryset = queryset.filter(model__icontains=model_query)
        try:
            if year_min: queryset = queryset.filter(year__gte=int(year_min))
            if year_max: queryset = queryset.filter(year__lte=int(year_max))
        except (ValueError, TypeError): pass
        try:
            if price_min: queryset = queryset.filter(price__gte=float(price_min))
            if price_max: queryset = queryset.filter(price__lte=float(price_max))
        except (ValueError, TypeError): pass

        # --- Apply Sorting ---
        # Get the 'order' parameter, default to 'price_low_to_high'
        order = self.request.GET.get('order', 'price_low_to_high')

        if order == 'price_low_to_high':
            queryset = queryset.order_by('price')
        elif order == 'price_high_to_low':
            queryset = queryset.order_by('-price')
        elif order == 'age_new_to_old':
            queryset = queryset.order_by('-year', '-pk')
        elif order == 'age_old_to_new':
            queryset = queryset.order_by('year', 'pk')
        else:
            queryset = queryset.order_by('price') # Default sort


        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get condition from kwargs or URL parameters
        condition_name = self.kwargs.get('condition_name')

        # Filter motorcycles based on condition for populating filter options
        filtered_motorcycles = Motorcycle.objects.filter(is_available=True)
        if condition_name:
            if condition_name == 'used':
                 filtered_motorcycles = filtered_motorcycles.filter(conditions__name__in=['used', 'demo']).distinct()
            else:
                filtered_motorcycles = filtered_motorcycles.filter(conditions__name=condition_name).distinct()


        # Get distinct brands from the filtered motorcycles
        context['brands'] = sorted(list(filtered_motorcycles.values_list('brand', flat=True).distinct()))

        # Get min and max years from the filtered motorcycles
        years = list(filtered_motorcycles.values_list('year', flat=True).distinct())
        if years:
            min_year = min(years)
            max_year = max(years)
            # Generate a continuous range of years from min to max
            context['years'] = list(range(max_year, min_year - 1, -1))
        else:
            context['years'] = []

        context['request'] = self.request

        # Add condition name to context if it was provided
        if condition_name:
            context['condition'] = condition_name # Keep the original context key name for templates
        return context


class NewMotorcycleListView(MotorcycleListView):
    template_name = 'motorcycles/new.html' # <--- CORRECTED: Set specific template here

    def get_queryset(self):
        # Set the condition_name kwarg for the base class's get_queryset
        self.kwargs['condition_name'] = 'new'
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_url_name'] = 'new'
        return context

class UsedMotorcycleListView(MotorcycleListView):
    template_name = 'motorcycles/used.html' # <--- CORRECTED: Set specific template here

    def get_queryset(self):
        # Set the condition_name kwarg to 'used' to filter for 'used' and 'demo' in the base class
        self.kwargs['condition_name'] = 'used'
        # The filtering for 'used' or 'demo' is handled in the base get_queryset now.
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_url_name'] = 'used'
        return context

class HireMotorcycleListView(MotorcycleListView):
    template_name = 'motorcycles/hire.html' # This was already correct

    def get_queryset(self):
        # Set the condition_name kwarg for the base class's get_queryset
        self.kwargs['condition_name'] = 'hire'
        queryset = super().get_queryset() # Start with the base filtered queryset

        # Filter by daily hire rate if provided (add this logic here)
        daily_rate_min = self.request.GET.get('daily_rate_min')
        daily_rate_max = self.request.GET.get('daily_rate_max')

        try:
            if daily_rate_min:
                queryset = queryset.filter(daily_hire_rate__gte=float(daily_rate_min))
            if daily_rate_max:
                queryset = queryset.filter(daily_hire_rate__lte=float(daily_rate_max))
        except (ValueError, TypeError):
            pass

        # Filter by availability based on selected date range
        hire_start_date = self.request.GET.get('hire_start_date')
        hire_end_date = self.request.GET.get('hire_end_date')

        if hire_start_date and hire_end_date:
            try:
                start_date = datetime.datetime.strptime(hire_start_date, '%Y-%m-%d').date()
                end_date = datetime.datetime.strptime(hire_end_date, '%Y-%m-%d').date()

                # Get motorcycles that don't have conflicting bookings
                # A booking conflicts if:
                # 1. Its start date falls within our requested period, or
                # 2. Its end date falls within our requested period, or
                # 3. It completely surrounds our requested period
                conflicting_bookings = HireBooking.objects.filter(
                    status__in=['confirmed', 'pending'], # Consider pending bookings too? Adjust as needed.
                    motorcycle__in=queryset,
                ).filter(
                    # booking starts during our period
                    Q(start_date__range=(start_date, end_date)) |
                    # booking ends during our period
                    Q(end_date__range=(start_date, end_date)) |
                    # booking surrounds our period
                    Q(start_date__lte=start_date, end_date__gte=end_date)
                ).values_list('motorcycle_id', flat=True)

                # Exclude motorcycles with conflicting bookings
                queryset = queryset.exclude(id__in=conflicting_bookings)

                # Add date range to context for display (handled in get_context_data)
                self.date_range = (start_date, end_date)
            except ValueError:
                # Invalid date format - filter none or return an error?
                # For now, we'll just proceed without date filtering
                pass

        return queryset


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_url_name'] = 'hire'

        # Add selected date range to context if it exists
        if hasattr(self, 'date_range'):
            context['hire_start_date'] = self.date_range[0].strftime('%Y-%m-%d') # Format for input field
            context['hire_end_date'] = self.date_range[1].strftime('%Y-%m-%d')   # Format for input field

            # Calculate total days for hire
            delta = self.date_range[1] - self.date_range[0]
            context['hire_days'] = delta.days + 1  # Include both start and end day

        return context


# These function views now call the appropriate class-based views
# Call as_view() without template_name argument, as it's set on the class
def new(request):
    view = NewMotorcycleListView.as_view()
    return view(request)

def used(request):
    view = UsedMotorcycleListView.as_view()
    return view(request)

def hire(request):
    view = HireMotorcycleListView.as_view()
    return view(request)