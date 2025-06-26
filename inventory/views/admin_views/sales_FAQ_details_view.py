# SCOOTER_SHOP/inventory/views/admin_views/sales_faq_details_view.py

from django.views.generic import DetailView
from inventory.models import SalesFAQ
from inventory.mixins import AdminRequiredMixin

class SalesFAQDetailsView(AdminRequiredMixin, DetailView):
    """
    View to display the details of a single Sales FAQ.
    """
    model = SalesFAQ
    template_name = 'inventory/admin_sales_faq_details.html'
    context_object_name = 'sales_faq'

    def get_context_data(self, **kwargs):
        """
        Adds the page title to the context.
        """
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"FAQ Details: {self.object.question[:50]}..."
        return context
