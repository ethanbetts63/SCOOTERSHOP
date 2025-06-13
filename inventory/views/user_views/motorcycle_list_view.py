# inventory/views/user_views/motorcycle_list_view.py

from django.views.generic import ListView
from inventory.models import Motorcycle # No need for MotorcycleCondition import here anymore
from inventory.utils.get_motorcycles_by_criteria import get_motorcycles_by_criteria
from inventory.utils.get_unique_makes_for_filter import get_unique_makes_for_filter

class MotorcycleListView(ListView):
    """
    Renders a list of motorcycles based on a condition slug using a class-based view.
    Handles 'new', 'used' (which includes 'demo'), and 'all' conditions.
    Provides context for filtering options like unique makes.
    """
    model = Motorcycle
    template_name = 'inventory/motorcycle_list.html'
    context_object_name = 'motorcycles'
    paginate_by = 10 # Example: paginate with 10 items per page

    def get_queryset(self):
        """
        Retrieves the queryset of motorcycles based on the condition slug
        passed in the URL kwargs, using the `get_motorcycles_by_criteria` utility.
        """
        condition_slug = self.kwargs.get('condition_slug')

        # Use the utility function to get the base queryset
        queryset = get_motorcycles_by_criteria(condition_slug=condition_slug)

        return queryset

    def get_context_data(self, **kwargs):
        """
        Adds extra context to the template, such as unique makes for filters
        and the current condition slug.
        """
        context = super().get_context_data(**kwargs)
        condition_slug = self.kwargs.get('condition_slug')

        # Get unique makes relevant to the current condition slug using the utility
        # The utility now correctly handles 'used' to include 'demo' for make filtering.
        unique_makes = get_unique_makes_for_filter(condition_slug=condition_slug)

        context['unique_makes'] = sorted(list(unique_makes)) # Ensure unique and sorted
        context['current_condition_slug'] = condition_slug
        context['page_title'] = f"{condition_slug.replace('-', ' ').title()} Motorcycles" if condition_slug else "All Motorcycles"

        # Add a list of years for the filter dropdowns (example: from 2000 to current year)
        import datetime
        current_year = datetime.date.today().year
        context['years'] = list(range(2000, current_year + 1))
        context['years'].reverse() # Newest first

        return context

