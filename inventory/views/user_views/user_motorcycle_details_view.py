from django.views.generic import DetailView
from django.http import Http404
from inventory.models import Motorcycle, InventorySettings
from inventory.utils.get_motorcycle_details import get_motorcycle_details
from inventory.utils.get_sales_faqs import get_faqs_for_step
from inventory.utils import get_featured_motorcycles


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

        context["sales_faqs"] = get_faqs_for_step("general")
        context["faq_title"] = "Questions About Our Motorcycles"

        # --- DEBUG: Logic to add related featured motorcycles ---
        print("\n--- Checking for featured motorcycles ---")
        
        # --- FIX: Determine category more robustly ---
        # Prioritize the ManyToManyField, then fall back to the CharField.
        category = None
        if motorcycle.conditions.exists():
            # Just take the first condition found (e.g., 'new' or 'used')
            primary_condition = motorcycle.conditions.first().name.lower()
            if primary_condition in ['new', 'used']:
                category = primary_condition
        
        # If no category found yet, check the simple field
        if not category and motorcycle.condition in ['new', 'used']:
            category = motorcycle.condition

        print(f"1. Determined motorcycle category: '{category}'")
        
        if category:
            featured_items = get_featured_motorcycles(category)
            print(f"2. Found {featured_items.count()} featured items initially for category '{category}'.")

            featured_items_after_exclude = featured_items.exclude(motorcycle=motorcycle)
            print(f"3. Found {featured_items_after_exclude.count()} featured items after excluding the current one.")
            
            context['featured_items'] = featured_items_after_exclude
            context['section_title'] = f"Other Featured {category.title()} Motorcycles"
            context['category'] = category
            
            print(f"4. Passing {featured_items_after_exclude.count()} items to the template.")
        else:
            print(f"2. No valid category ('new' or 'used') found. Skipping featured section.")
            
        print("--- End of featured check ---\n")

        return context
