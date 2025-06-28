# service/views/admin_views/service_faq_delete_view.py

from django.views.generic.edit import DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from service.models import ServiceFAQ
from inventory.mixins import AdminRequiredMixin # Assuming a shared mixin

class ServiceFAQDeleteView(AdminRequiredMixin, DeleteView):
    """
    View to handle the deletion of a Service FAQ.
    """
    model = ServiceFAQ
    success_url = reverse_lazy('service:service_faq_management')
    # A generic confirmation template can be reused from another app
    # or you can create one at 'service/admin_confirm_delete.html'
    template_name = 'service/admin_confirm_delete.html' 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Confirm Delete FAQ"
        context['object_type'] = "Service FAQ"
        context['object_name'] = self.object.question
        context['cancel_url'] = self.success_url
        return context

    def form_valid(self, form):
        """
        Adds a success message before deleting the object.
        """
        messages.success(self.request, f"The Service FAQ '{self.object.question[:50]}...' was deleted successfully.")
        return super().form_valid(form)
