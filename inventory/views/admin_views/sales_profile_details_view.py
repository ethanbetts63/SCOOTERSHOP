from django.views.generic import DetailView
from inventory.mixins import AdminRequiredMixin

from inventory.models import SalesProfile


class SalesProfileDetailsView(AdminRequiredMixin, DetailView):
    model = SalesProfile
    template_name = "inventory/admin_sales_profile_details.html"
    context_object_name = "sales_profile"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Sales Profile Details: {self.object.name}"
        return context
