# inventory/views/motorcycle_delete_view.py

from django.views.generic import DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages

from inventory.models import Motorcycle


class MotorcycleDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """View for deleting a motorcycle listing."""
    model = Motorcycle
    'inventory/templates/inventory/motorcycle_confirm_delete.html'
    success_url = reverse_lazy('core:index') # Redirect to index or motorcycle list after deletion

    def test_func(self):
        """Only staff can delete motorcycles."""
        # Assuming staff are the only ones who manage inventory, the is_staff check is sufficient.
        return self.request.user.is_staff

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, f"Motorcycle '{self.get_object()}' deleted successfully!")
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Delete Motorcycle'
        return context