from django.views.generic import DetailView
from inventory.mixins import AdminRequiredMixin

from inventory.models import Motorcycle


class AdminMotorcycleDetailsView(AdminRequiredMixin, DetailView):
    model = Motorcycle
    template_name = "inventory/admin_motorcycle_details.html"
    context_object_name = "motorcycle"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Motorcycle Details: {self.object.title}"
        return context
