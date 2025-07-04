from django.views.generic import ListView
from django.db.models import Count
from inventory.models import SalesTerms
from inventory.mixins import AdminRequiredMixin


class SalesTermsManagementView(AdminRequiredMixin, ListView):
    model = SalesTerms
    template_name = "inventory/admin_terms_and_conditions_management.html"
    context_object_name = "terms_versions"
    paginate_by = 10

    def get_queryset(self):
        return SalesTerms.objects.annotate(
            booking_count=Count('sales_bookings')
        ).order_by('-version_number')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Sales Terms & Conditions Management"
        return context
