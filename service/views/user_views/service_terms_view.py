from django.views.generic import TemplateView
from service.models import ServiceTerms
from refunds.models import RefundTerms
from dashboard.models import SiteSettings


class ServiceTermsView(TemplateView):
    template_name = "service/service_terms.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_terms = ServiceTerms.objects.filter(is_active=True).first()
        context["page_title"] = "Service Booking Terms & Conditions"
        context["terms"] = active_terms

        settings = SiteSettings.get_settings()
        if settings.enable_refunds:
            refund_terms = RefundTerms.objects.filter(is_active=True).first()
            context["refund_terms"] = refund_terms

        return context
