from django.views.generic import TemplateView
from payments.models import RefundPolicy

class RefundPolicyView(TemplateView):
    template_name = "payments/refund_policy.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['refund_policy'] = RefundPolicy.objects.filter(is_active=True).first()
        context['page_title'] = "Refund Policy"
        return context
