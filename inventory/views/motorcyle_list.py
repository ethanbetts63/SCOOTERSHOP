# inventory/views/motorcycle_list.py

from django.shortcuts import render
from django.views.generic import ListView
from django.db.models import Q
import datetime
from django.contrib import messages # Import messages for potential future use

# Import models from the inventory app
from inventory.models import Motorcycle, MotorcycleCondition, HireBooking
# Import utility function from the inventory app
from inventory.utils import get_featured_motorcycles


class MotorcycleListView(ListView):
    model = Motorcycle
    # This default template_name might not be used directly if subclasses override it
    # but it's fine to keep as a fallback or for a potential base list view.
    # Updated template path
    template_name = 'inventory/motorcycles/motorcycle_list.html'
    context_object_name = 'motorcycles'
    paginate_by = 12

    def get_queryset(self):
        # Start with base queryset (available motorcycles)
        queryset = super().get_queryset().filter(is_available=True)

        # Apply condition filter if specified in view kwargs or URL parameters
        # Check both kwargs (from urls.py with {'condition_name': '...'})
        # and GET parameters (less standard for primary filtering, but could be used)
        condition_name = self.kwargs.get('condition_name') or self.request.GET.get('condition')

        if condition_name:
            # Use the new conditions ManyToManyField
            if condition_name.lower() == 'used':
                 # Filter for motorcycles that have 'used' OR 'demo' in their conditions
                 queryset = queryset.filter(conditions__name__in=['used', 'demo']).distinct()
            elif condition_name.lower() in ['new', 'hire']:
                 # Filter for motorcycles that have the specific condition
                 queryset = queryset.filter(conditions__name__iexact=condition_name).distinct()
            # Note: Consider adding a case for an invalid condition_name

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
            queryset = queryset.order_by('-year', '-pk') # Added '-pk' for stable sort
        elif order == 'age_old_to_new':
            queryset = queryset.order_by('year', 'pk') # Added 'pk' for stable sort
        else:
            queryset = queryset.order_by('price') # Default sort


        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get condition from kwargs or URL parameters
        condition_name = self.kwargs.get('condition_name') or self.request.GET.get('condition')

        # Filter motorcycles based on condition for populating filter options
        # Start with the full set of available motorcycles before applying request filters
        filtered_for_options = Motorcycle.objects.filter(is_available=True)

        if condition_name:
            if condition_name.lower() == 'used':
                 filtered_for_options = filtered_for_options.filter(conditions__name__in=['used', 'demo']).distinct()
            elif condition_name.lower() in ['new', 'hire']:
                filtered_for_options = filtered_for_options.filter(conditions__name__iexact=condition_name).distinct()


        # Get distinct brands from the filtered motorcycles
        context['brands'] = sorted(list(filtered_for_options.values_list('brand', flat=True).distinct()))

        # Get min and max years from the filtered motorcycles
        years = list(filtered_for_options.values_list('year', flat=True).distinct())
        if years:
            min_year = min(years)
            max_year = max(years)
            # Generate a continuous range of years from max to min
            context['years'] = list(range(max_year, min_year - 1, -1))
        else:
            context['years'] = [] # Ensure it's an empty list if no years found

        context['request'] = self.request # Pass the request object to the template

        # Add condition name to context if it was provided
        if condition_name:
            # Pass both the original case and lowercase for flexibility in templates
            context['condition'] = condition_name
            context['condition_lower'] = condition_name.lower()

        # Pass the current sorting order to the template for filter persistence
        context['current_order'] = self.request.GET.get('order', 'price_low_to_high')


        return context


class NewMotorcycleListView(MotorcycleListView):
    # Updated template path
    template_name = 'inventory/motorcycles/new.html'

    def get_queryset(self):
        # Set the condition_name kwarg for the base class's get_queryset
        self.kwargs['condition_name'] = 'new'
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Updated current_url_name to use the app namespace
        context['current_url_name'] = 'inventory:inventory_new' # Using the specific URL name from inventory/urls.py
        return context

class UsedMotorcycleListView(MotorcycleListView):
    # Updated template path
    template_name = 'inventory/motorcycles/used.html'

    def get_queryset(self):
        # Set the condition_name kwarg to 'used' to filter for 'used' and 'demo' in the base class
        self.kwargs['condition_name'] = 'used'
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Updated current_url_name to use the app namespace
        context['current_url_name'] = 'inventory:used' # Using the specific URL name from inventory/urls.py
        return context

class HireMotorcycleListView(MotorcycleListView):
    # Updated template path
    template_name = 'inventory/motorcycles/hire.html'

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
            # Optionally add a message if the rate input is invalid
            # messages.error(self.request, "Invalid rate input.")
            pass

        # Filter by availability based on selected date range
        hire_start_date_str = self.request.GET.get('hire_start_date')
        hire_end_date_str = self.request.GET.get('hire_end_date')

        if hire_start_date_str and hire_end_date_str:
            try:
                start_date = datetime.datetime.strptime(hire_start_date_str, '%Y-%m-%d').date()
                end_date = datetime.datetime.strptime(hire_end_date_str, '%Y-%m-%d').date()

                # Add validation: Ensure start date is not after end date
                if start_date > end_date:
                     messages.error(self.request, "Hire start date cannot be after the end date.")
                     # Return an empty queryset or the queryset before date filtering
                     return self.model.objects.none() # Return no results if dates are invalid

                # Get motorcycles that don't have conflicting bookings
                # A booking conflicts if:
                # 1. Its start date falls within our requested period, or
                # 2. Its end date falls within our requested period, or
                # 3. It completely surrounds our requested period
                # 4. Our requested period falls within its booking period
                conflicting_bookings = HireBooking.objects.filter(
                    status__in=['confirmed', 'pending'], # Consider pending bookings too? Adjust as needed.
                    motorcycle__in=queryset,
                ).filter(
                    Q(start_date__lte=end_date, end_date__gte=start_date)
                    # Simplified check: Booking period overlaps with the requested period
                    # (Booking starts before or on requested end date AND booking ends after or on requested start date)
                ).values_list('motorcycle_id', flat=True)

                # Exclude motorcycles with conflicting bookings
                queryset = queryset.exclude(id__in=conflicting_bookings)

                # Add date range to context for display (handled in get_context_data)
                self.date_range = (start_date, end_date)
            except ValueError:
                # Invalid date format - filter none and show an error message
                messages.error(self.request, "Invalid date format. Please use YYYY-MM-DD.")
                return self.model.objects.none() # Return no results on invalid date format
            except Exception as e:
                # Catch any other potential errors during date processing
                messages.error(self.request, f"An error occurred while filtering by date: {e}")
                return self.model.objects.none() # Return no results on other errors


        return queryset


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Updated current_url_name to use the app namespace
        context['current_url_name'] = 'inventory:hire' # Using the specific URL name from inventory/urls.py

        # Add selected date range to context if it exists
        if hasattr(self, 'date_range'):
            context['hire_start_date'] = self.date_range[0].strftime('%Y-%m-%d') # Format for input field
            context['hire_end_date'] = self.date_range[1].strftime('%Y-%m-%d')   # Format for input field

            # Calculate total days for hire
            delta = self.date_range[1] - self.date_range[0]
            context['hire_days'] = delta.days + 1  # Include both start and end day
        else:
            # Provide empty strings if no date range selected, to prevent template errors
            context['hire_start_date'] = ''
            context['hire_end_date'] = ''
            context['hire_days'] = None


        return context


# These function views now call the appropriate class-based views
# Call as_view() without template_name argument, as it's set on the class
# These are kept to match the provided inventory/urls.py structure.
# Consider updating urls.py to use ClassName.as_view() directly for simplicity.
def new(request):
    view = NewMotorcycleListView.as_view()
    return view(request)

def used(request):
    view = UsedMotorcycleListView.as_view()
    return view(request)

def hire(request):
    view = HireMotorcycleListView.as_view()
    return view(request)