# # inventory/views/all_motorcycle_list_view.py

# from django.shortcuts import redirect
# from django.views.generic import ListView
# from inventory.models import Motorcycle
# from .motorcycle_list_view import MotorcycleListView # Import the base class


# # Lists all motorcycles (available or not, for admin view)
# class AllMotorcycleListView(MotorcycleListView):
#     template_name = 'inventory/all.html'

#     def get_queryset(self):
#         # Start with ALL motorcycles, available or not, for the admin view
#         queryset = Motorcycle.objects.all()

#         # --- Add Availability Filtering ---
#         availability_filter = self.request.GET.get('availability', 'all') # Default to 'all'

#         if availability_filter == 'available':
#             queryset = queryset.filter(is_available=True)
#         elif availability_filter == 'unavailable':
#             queryset = queryset.filter(is_available=False)
#         # If 'all' or other value, no additional filtering on is_available is applied here

#         # Apply common filters and sorting using the helper from the base class
#         # Common filters (brand, model, year, price) are applied to ALL bikes here
#         queryset = self._apply_common_filters_and_sorting(queryset)

#         return queryset

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)

#         # Corrected: For the AllMotorcycleListView, filter options should include all bikes
#         filtered_for_options = Motorcycle.objects.all()

#         context['brands'] = sorted(list(filtered_for_options.values_list('brand', flat=True).distinct()))

#         years = list(filtered_for_options.values_list('year', flat=True).distinct())
#         if years:
#             min_year = min(years)
#             max_year = max(years)
#             context['years'] = list(range(max_year, min_year - 1, -1))
#         else:
#             context['years'] = []

#         # The 'condition' context variable might not be needed or should be handled differently
#         # for the 'all' view if filtering by condition isn't the primary purpose.
#         # Removing or adjusting the condition-related context if necessary for this view.
#         context.pop('condition', None)
#         context.pop('condition_lower', None)

#         # --- Add availability filter to context ---
#         context['current_availability_filter'] = self.request.GET.get('availability', 'all')


#         return context


#     def dispatch(self, request, *args, **kwargs):
#         if not request.user.is_staff:
#             # Optionally add a message here before redirecting
#             # messages.warning(request, "You do not have permission to access this page.")
#             return redirect('core:index')
#         return super().dispatch(request, *args, **kwargs)