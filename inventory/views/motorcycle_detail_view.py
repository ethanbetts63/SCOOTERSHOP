# # inventory/views/motorcycle_detail_view.py

# from django.shortcuts import render, get_object_or_404
# from django.views.generic import DetailView
# from django.conf import settings

# from inventory.models import Motorcycle, MotorcycleImage, MotorcycleCondition
# # Assuming .utils exists and has get_featured_motorcycles
# # from .utils import get_featured_motorcycles

# # Mock get_featured_motorcycles if .utils is not available in this environment
# # If you have a .utils file, remove this mock function
# def get_featured_motorcycles(exclude_id, limit, condition):
#     """
#     Mock function for get_featured_motorcycles.
#     Replace with actual import if .utils is available.
#     """
#     # print(f"Mock get_featured_motorcycles called with exclude_id={exclude_id}, limit={limit}, condition={condition}")
#     return []


# class MotorcycleDetailView(DetailView):
#     """Displays detailed information about a specific motorcycle."""
#     model = Motorcycle
#     template_name = 'inventory/motorcycle_detail.html'
#     context_object_name = 'motorcycle'

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         # Add additional images to context
#         additional_images = self.object.images.all()
#         context['additional_images'] = additional_images

#         # Determine which condition to use for featured motorcycles
#         # Use the first condition associated with the motorcycle for simplicity in featured logic
#         # Safely access condition name
#         motorcycle_condition_name = self.object.conditions.first().name if self.object.conditions.first() else None
#         featured_condition = motorcycle_condition_name.lower() if motorcycle_condition_name else None

#         # Get featured motorcycles with the appropriate condition
#         featured = get_featured_motorcycles(
#             exclude_id=self.object.pk,
#             limit=3,
#             condition=featured_condition # Pass the determined condition
#         )
#         context['featured_motorcycles'] = featured

#         # Set the appropriate condition in the context for the template
#         # This determines which "View All" link to show
#         # Pass the original case condition name if available
#         context['condition'] = motorcycle_condition_name
#         # Pass the lowercase for comparison in templates
#         context['condition_lower'] = featured_condition

#         # Determine if the motorcycle has the 'hire' or 'new' condition for filtering specs
#         is_for_hire = self.object.conditions.filter(name='hire').exists()
#         is_new = self.object.conditions.filter(name='new').exists()
#         is_for_sale = self.object.conditions.filter(name__in=['new', 'used', 'demo']).exists() # Check if any sale condition is present

#         # Define specifications with their labels and icons
#         motorcycle = self.object
#         specifications = []

#         # Always include condition if available
#         if motorcycle.conditions.exists():
#              specifications.append({'field': 'condition', 'label': 'Condition', 'icon': 'icon-category', 'value': motorcycle.get_conditions_display()})

#         # Conditionally add other specifications
#         if motorcycle.year is not None: specifications.append({'field': 'year', 'label': 'Year', 'icon': 'icon-year', 'value': motorcycle.year})
#         # Odometer is now always required, so include it if its value exists (should always exist if required)
#         if motorcycle.odometer is not None: specifications.append({'field': 'odometer', 'label': 'Odometer', 'icon': 'icon-odometer', 'value': f"{motorcycle.odometer} km"})
#         if motorcycle.engine_size: specifications.append({'field': 'engine_size', 'label': 'Engine', 'icon': 'icon-capacity', 'value': f"{motorcycle.engine_size}cc"}) # Assuming engine_size remains required/always has a value
#         if motorcycle.seats is not None: specifications.append({'field': 'seats', 'label': 'Seats', 'icon': 'icon-seat', 'value': motorcycle.seats})
#         if motorcycle.transmission: specifications.append({'field': 'transmission', 'label': 'Transmission', 'icon': 'icon-transmission', 'value': motorcycle.transmission})
#         # Include Rego/Rego Expiry if not New
#         if motorcycle.rego and not is_new: specifications.append({'field': 'rego', 'label': 'Registration', 'icon': 'icon-rego', 'value': motorcycle.rego})
#         if motorcycle.rego_exp and not is_new: specifications.append({'field': 'rego_exp', 'label': 'Rego Expires', 'icon': 'icon-rego-exp', 'value': motorcycle.rego_exp.strftime("%d %b %Y")})
#         # Include Stock Number if New, Used, or Demo
#         if motorcycle.stock_number and is_for_sale: specifications.append({'field': 'stock_number', 'label': 'Stock #', 'icon': 'icon-stock', 'value': motorcycle.stock_number})

#         # Handle price display logic - always add the price field if any sale condition is present
#         if is_for_sale:
#             price_value = f"${motorcycle.price:.2f}" if motorcycle.price is not None else "Contact for price"
#             specifications.append({'field': 'price', 'label': 'Price', 'icon': 'icon-money', 'value': price_value})

#         # Handle hire rate display logic - always add the daily hire rate if hire condition is present
#         if is_for_hire:
#             # Assuming you have a settings.DEFAULT_DAILY_HIRE_RATE
#             default_daily_rate = getattr(settings, 'DEFAULT_DAILY_HIRE_RATE', None)
#             daily_rate_value = f"${motorcycle.daily_hire_rate:.2f}" if motorcycle.daily_hire_rate is not None else (f"Default ({default_daily_rate:.2f})" if default_daily_rate is not None else "Contact for rate")
#             specifications.append({'field': 'daily_hire_rate', 'label': 'Daily Hire Rate', 'icon': 'icon-money', 'value': daily_rate_value})
#              # Add other hire rates if they exist
#             if motorcycle.hourly_hire_rate is not None:
#                  specifications.append({'field': 'hourly_hire_rate', 'label': 'Hourly Rate', 'icon': 'icon-money', 'value': f"${motorcycle.hourly_hire_rate:.2f}"})
#         context['filtered_specifications'] = specifications

#         return context