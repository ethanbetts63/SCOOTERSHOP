from django.views.generic import DetailView
from inventory.models import SalesTerms
from inventory.mixins import AdminRequiredMixin


class SalesTermsDetailsView(AdminRequiredMixin, DetailView):
    model = SalesTerms
    template_name = "inventory/admin_terms_and_conditions_detail.html"
    context_object_name = "terms_version"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"View T&C Version {self.object.version_number}"
        return context
