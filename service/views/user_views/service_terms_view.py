from django.views.generic import TemplateView
from service.models import ServiceTerms

class ServiceTermsView(TemplateView):
    template_name = "service/service_terms.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_terms = ServiceTerms.objects.filter(is_active=True).first()
        context["page_title"] = "Service Booking Terms & Conditions"
        context["terms"] = active_terms
        return context
