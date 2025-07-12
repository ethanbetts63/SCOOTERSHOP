from django.views.generic import ListView
from refunds.models import RefundTerms
from dashboard.mixins import AdminRequiredMixin

class AdminRefundTermsManagementView(AdminRequiredMixin, ListView):
    model = RefundTerms
    template_name = "refunds/admin_refund_terms_management.html"
    context_object_name = "terms_versions"
    paginate_by = 10

    def get_queryset(self):
        return RefundTerms.objects.all().order_by('-version_number')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Refund Policy Terms Management"
        return context
