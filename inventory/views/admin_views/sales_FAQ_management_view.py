# SCOOTER_SHOP/inventory/views/admin_views/sales_faq_management_view.py

from django.db.models import Q
from django.views.generic import ListView
from inventory.models import SalesFAQ
from inventory.mixins import AdminRequiredMixin

class SalesFAQManagementView(AdminRequiredMixin, ListView):
    """
    View for admin to manage (list, search) Sales FAQs.
    """
    model = SalesFAQ
    template_name = 'inventory/admin_sales_faq_management.html'
    context_object_name = 'sales_faqs'
    paginate_by = 15

    def get_queryset(self):
        """
        Overrides the default queryset to allow searching.
        """
        queryset = super().get_queryset().order_by('booking_step', 'display_order')
        search_term = self.request.GET.get('q', '').strip()

        if search_term:
            # Filters by question, answer, or the booking step choice's key (e.g., 'step1')
            queryset = queryset.filter(
                Q(question__icontains=search_term) |
                Q(answer__icontains=search_term) |
                Q(booking_step__icontains=search_term)
            ).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        """
        Adds search term and page title to the context.
        """
        context = super().get_context_data(**kwargs)
        context['search_term'] = self.request.GET.get('q', '')
        context['page_title'] = "Sales FAQs Management"
        return context
