from django.views.generic import TemplateView
from django.db.models import Q
from inventory.models import FeaturedMotorcycle

class FeaturedMotorcycleManagementView(TemplateView):
    """
    Displays the management page for featured motorcycles, separating them
    into 'New' and 'Used' categories.
    """
    template_name = "inventory/admin_featured_motorcycle_management.html"

    def get_context_data(self, **kwargs):
        """
        Retrieves the context data for rendering the template.
        This now correctly queries both the 'condition' and 'conditions'
        fields on the related Motorcycle model.
        """
        context = super().get_context_data(**kwargs)

        # --- FIX: Use a Q object to check both condition fields ---
        new_filter = Q(motorcycle__condition='new') | Q(motorcycle__conditions__name__iexact='new')
        used_filter = Q(motorcycle__condition='used') | Q(motorcycle__conditions__name__iexact='used')

        # Filter FeaturedMotorcycle objects based on the related motorcycle's condition
        context['featured_new'] = FeaturedMotorcycle.objects.filter(new_filter).distinct().order_by('order')
        context['featured_used'] = FeaturedMotorcycle.objects.filter(used_filter).distinct().order_by('order')
        
        return context
