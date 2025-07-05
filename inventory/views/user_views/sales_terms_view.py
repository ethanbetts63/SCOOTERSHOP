from django.views.generic import TemplateView
from inventory.models import SalesTerms

# Add this class to your user_views.py file
class SalesTermsView(TemplateView):
    """
    A view to display the currently active sales terms and conditions.
    """
    template_name = "inventory/sales_terms.html"

    def get_context_data(self, **kwargs):
        """
        Adds the active sales terms to the context.
        """
        context = super().get_context_data(**kwargs)
        
        # Find the single active SalesTerms instance.
        active_terms = SalesTerms.objects.filter(is_active=True).first()
        
        context["page_title"] = "Sales Terms & Conditions"
        context["terms"] = active_terms
        return context
