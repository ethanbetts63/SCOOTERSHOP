from django.views.generic import DetailView
from refunds.models import RefundTerms
from dashboard.mixins import AdminRequiredMixin

class AdminRefundTermsDetailsView(AdminRequiredMixin, DetailView):
    model = RefundTerms
    template_name = "payments/admin_refund_terms_details.html"
    context_object_name = "terms_version"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"View Refund Policy Version {self.object.version_number}"
        return context
