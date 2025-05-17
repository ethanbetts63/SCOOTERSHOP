# inventory/views/motorcycle_update_view.py

from django.views.generic import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy

from inventory.models import Motorcycle
from inventory.forms import MotorcycleForm
from .motorcycle_form_handler_mixin import MotorcycleFormHandlerMixin


class MotorcycleUpdateView(LoginRequiredMixin, UserPassesTestMixin, MotorcycleFormHandlerMixin, UpdateView):
    """View for updating an existing motorcycle listing."""
    model = Motorcycle
    form_class = MotorcycleForm
    template_name = 'inventory/motorcycle_form.html'
    # success_url is defined by get_success_url

    def test_func(self):
        """Only staff can update motorcycles."""
        # Assuming staff are the only ones who manage inventory, the is_staff check is sufficient.
        return self.request.user.is_staff

    # form_valid is handled by the mixin now, but we can override to add messages
    def form_valid(self, form):
        """Handle form valid and add success message."""
        # The form_valid logic is now largely handled by the mixin.
        # Call the mixin's form_valid which will save and redirect if formset is also valid.
        response = super().form_valid(form)
        # The success message is added within the mixin's form_valid before the super call
        return response


    def get_success_url(self):
        """Redirect to the detail page of the updated motorcycle."""
        # This will only be called if form_valid (and thus formset validation) succeeded
        return reverse_lazy('inventory:motorcycle-detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_update_view'] = True
        context['page_title'] = f'Edit {self.object.year} {self.object.brand} {self.object.model}'
        return context