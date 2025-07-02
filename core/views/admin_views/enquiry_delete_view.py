from django.views.generic.edit import DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from core.models.enquiry import Enquiry
from inventory.mixins import AdminRequiredMixin

class EnquiryDeleteView(AdminRequiredMixin, DeleteView):
    model = Enquiry
    
    def get_success_url(self):
        messages.success(self.request, f"Enquiry from {self.object.name} was deleted successfully.")
        return reverse_lazy('core:enquiry_management')

    def get(self, request, *args, **kwargs):
        # This handles direct GET requests to the delete URL, preventing accidental deletion
        # Instead of showing a confirmation template, it redirects with a message.
        messages.info(request, "Please confirm deletion via the management page.")
        return redirect(reverse_lazy('core:enquiry_management'))

    def post(self, request, *args, **kwargs):
        # This method is called when the form is submitted (e.g., from a button click)
        self.object = self.get_object()
        self.object.delete()
        return self.get_success_url()
