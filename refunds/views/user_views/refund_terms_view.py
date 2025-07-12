from django.views.generic import TemplateView
from refunds.models import RefundTerms

class RefundTermsView(TemplateView):
    template_name = "payments/refund_terms.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['refund_policy'] = RefundTerms.objects.filter(is_active=True).first()
        context['page_title'] = "Refund Policy"
        return context
