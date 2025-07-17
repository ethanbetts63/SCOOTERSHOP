from django.views.generic import DetailView
from service.models import ServiceTerms
from service.mixins import AdminRequiredMixin


class ServiceTermsDetailsView(AdminRequiredMixin, DetailView):
    model = ServiceTerms
    template_name = "service/admin_service_terms_details.html"
    context_object_name = "terms_version"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"View Service T&C Version {self.object.version_number}"
        return context
