from django.views.generic.edit import DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from inventory.models import Salesfaq
from inventory.mixins import AdminRequiredMixin


class SalesfaqDeleteView(AdminRequiredMixin, DeleteView):
    model = Salesfaq
    success_url = reverse_lazy("inventory:sales_faq_management")
    template_name = "inventory/admin_confirm_delete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Confirm Delete faq"
        context["object_type"] = "Sales faq"
        context["object_name"] = self.object.question
        return context

    def form_valid(self, form):
        messages.success(
            self.request,
            f"The faq '{self.object.question[:50]}...' was deleted successfully.",
        )
        return super().form_valid(form)
