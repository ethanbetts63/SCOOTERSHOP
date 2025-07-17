from django.views.generic import DetailView
from refunds.models import RefundTerms


class AdminRefundTermsDetailView(DetailView):
    model = RefundTerms
    template_name = "refunds/admin_refund_terms_details.html"
    context_object_name = "terms_version"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Refund Terms Details"
        return context
