from django.views.generic import TemplateView
from service.models import ServiceTerms

class ServiceBookingTermsView(TemplateView):
    """
    A view to display the currently active service booking terms and conditions.
    """
    template_name = "service/service_booking_terms.html"

    def get_context_data(self, **kwargs):
        """
        Adds the active service terms to the context.
        """
        context = super().get_context_data(**kwargs)
        
        # Find the single active ServiceTerms instance.
        active_terms = ServiceTerms.objects.filter(is_active=True).first()
        
        context["page_title"] = "Service Booking Terms & Conditions"
        context["terms"] = active_terms
        return context
