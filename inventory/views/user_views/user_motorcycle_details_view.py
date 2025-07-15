from django.views.generic import DetailView
from django.http import Http404
from inventory.models import Motorcycle, InventorySettings
from inventory.utils.get_motorcycle_details import get_motorcycle_details
from inventory.utils.get_sales_faqs import get_faqs_for_step
from inventory.utils import get_featured_motorcycles
from inventory.utils.has_available_date import (
    has_available_date_for_deposit_flow,
    has_available_date_for_viewing_flow
)


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

        # Check availability for each flow type separately
        context['can_reserve_with_deposit'] = has_available_date_for_deposit_flow(inventory_settings)
        context['can_book_viewing'] = has_available_date_for_viewing_flow(inventory_settings)

        # Determine if the motorcycle is reserved based on active bookings with deposit paid
        is_reserved = motorcycle.sales_bookings.filter(
            booking_status__in=["pending_confirmation", "confirmed"],
            payment_status="deposit_paid"
        ).exists()
        context['is_reserved'] = is_reserved

        context["sales_faqs"] = get_faqs_for_step("general")
        context["faq_title"] = "Questions About Our Motorcycles"        
        category = None
        if motorcycle.conditions.exists():
            primary_condition = motorcycle.conditions.first().name.lower()
            if primary_condition in ['new', 'used']:
                category = primary_condition
        
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
