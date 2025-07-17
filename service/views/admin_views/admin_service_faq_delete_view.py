from django.views.generic.edit import DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from service.models import Servicefaq
from inventory.mixins import AdminRequiredMixin


class ServicefaqDeleteView(AdminRequiredMixin, DeleteView):
    model = Servicefaq
    success_url = reverse_lazy("service:service_faq_management")

    template_name = "service/admin_confirm_delete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Confirm Delete faq"
        context["object_type"] = "Service faq"
        context["object_name"] = self.object.question
        context["cancel_url"] = self.success_url
        return context

    def form_valid(self, form):
        messages.success(
            self.request,
            f"The Service faq '{self.object.question[:50]}...' was deleted successfully.",
        )
        return super().form_valid(form)
