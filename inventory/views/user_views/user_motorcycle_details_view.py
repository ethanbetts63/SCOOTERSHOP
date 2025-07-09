from django.views.generic import DetailView
from django.http import Http404
from inventory.models import Motorcycle, InventorySettings
from inventory.utils.get_motorcycle_details import get_motorcycle_details
from inventory.utils.get_sales_faqs import get_faqs_for_step
from inventory.utils import get_featured_motorcycles
from inventory.utils.get_sales_appointment_date_info import get_sales_appointment_date_info
from datetime import timedelta, datetime


class UserMotorcycleDetailsView(DetailView):
    model = Motorcycle
    template_name = "inventory/user_motorcycle_details.html"
    context_object_name = "motorcycle"
    pk_url_kwarg = "pk"

    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg)
        motorcycle = get_motorcycle_details(pk)
        if not motorcycle:
            raise Http404("Motorcycle not found or does not exist.")
        return motorcycle

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        motorcycle = self.object
        
        inventory_settings = InventorySettings.objects.first()
        context["inventory_settings"] = inventory_settings

        # More robust check for available appointment dates
        is_appointment_date_available = False
        if inventory_settings:
            min_date, max_date, blocked_dates_str = get_sales_appointment_date_info(inventory_settings)
            
            # Generate a set of all possible dates in the range
            all_possible_dates = set()
            if max_date >= min_date:
                current_date = min_date
                while current_date <= max_date:
                    all_possible_dates.add(current_date)
                    current_date += timedelta(days=1)

            # Convert the list of blocked date strings to a set of date objects
            blocked_dates_obj = set()
            for date_str in blocked_dates_str:
                try:
                    blocked_dates_obj.add(datetime.strptime(date_str, "%Y-%m-%d").date())
                except (ValueError, TypeError):
                    continue # Ignore invalid date strings

            # The available dates are the difference between all possible dates and blocked dates
            available_dates = all_possible_dates - blocked_dates_obj
            
            # If there is at least one available date, set the flag to True
            if available_dates:
                is_appointment_date_available = True
        
        context['is_appointment_date_available'] = is_appointment_date_available

        context["sales_faqs"] = get_faqs_for_step("general")
        context["faq_title"] = "Questions About Our Motorcycles"        
        category = None
        if motorcycle.conditions.exists():
            primary_condition = motorcycle.conditions.first().name.lower()
            if primary_condition in ['new', 'used']:
                category = primary_condition
        
        # If no category found yet, check the simple field
        if not category and motorcycle.condition in ['new', 'used']:
            category = motorcycle.condition

        
        if category:
            featured_items = get_featured_motorcycles(category)

            featured_items_after_exclude = featured_items.exclude(motorcycle=motorcycle)
            
            context['featured_items'] = featured_items_after_exclude
            context['section_title'] = f"Other Featured {category.title()} Motorcycles"
            context['category'] = category
            
        else:
            pass            

        return context
