# inventory/views/user_views/motorcycle_list_view.py

from django.views.generic import ListView
from django.db.models import Q # Import Q object for complex lookups
from inventory.models import Motorcycle, MotorcycleCondition
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
        passed in the URL kwargs. Handles special logic for 'used' condition.
        """
        condition_slug = self.kwargs.get('condition_slug')

        if condition_slug == 'used':
            # For 'used', we want to include both 'used' and 'demo' conditions.
            # get_motorcycles_by_criteria currently takes a single slug.
            # We will manually combine here or enhance get_motorcycles_by_criteria if needed.
            # A Q object allows for OR conditions.
            queryset = Motorcycle.objects.filter(
                Q(condition__display_name__iexact='used') | Q(condition__display_name__iexact='demo')
            ).order_by('brand', 'model', 'year')
        elif condition_slug == 'all':
            # 'all' means no specific condition filter, so fetch all motorcycles
            queryset = Motorcycle.objects.all().order_by('brand', 'model', 'year')
        elif condition_slug:
            # For specific conditions like 'new'
            try:
                condition_obj = MotorcycleCondition.objects.get(display_name__iexact=condition_slug)
                queryset = Motorcycle.objects.filter(condition=condition_obj).order_by('brand', 'model', 'year')
            except MotorcycleCondition.DoesNotExist:
                queryset = Motorcycle.objects.none() # No motorcycles match this condition
        else:
            # Default to all if no condition_slug is provided (e.g., if URL allows it)
            queryset = Motorcycle.objects.all().order_by('brand', 'model', 'year')

        # Note: The initial implementation of `get_motorcycles_by_criteria` was designed for
        # function-based views. For class-based views, we can directly use Django ORM
        # filters as shown above within `get_queryset`. If you want to strictly adhere
        # to the `get_motorcycles_by_criteria` utility, it would need to be updated
        # to accept a list of condition slugs or handle the 'used'/'demo' combination internally.
        # For this CBV, I've opted for direct ORM filtering using Q objects for clarity.

        return queryset

    def get_context_data(self, **kwargs):
        """
        Adds extra context to the template, such as unique makes for filters
        and the current condition slug.
        """
        context = super().get_context_data(**kwargs)
        condition_slug = self.kwargs.get('condition_slug')

        # Determine the effective condition slugs for unique makes calculation
        # The `get_unique_makes_for_filter` utility takes a single condition_slug.
        # To get makes for 'used' + 'demo', we'll call it twice and combine.
        unique_makes = set()
        if condition_slug == 'used':
            unique_makes.update(get_unique_makes_for_filter(condition_slug='used'))
            unique_makes.update(get_unique_makes_for_filter(condition_slug='demo'))
        elif condition_slug == 'all':
            unique_makes.update(get_unique_makes_for_filter(condition_slug=None)) # None for all
        else:
            unique_makes.update(get_unique_makes_for_filter(condition_slug=condition_slug))

        context['unique_makes'] = sorted(list(unique_makes))
        context['current_condition_slug'] = condition_slug
        context['page_title'] = f"{condition_slug.replace('-', ' ').title()} Motorcycles" if condition_slug else "All Motorcycles"

        return context

