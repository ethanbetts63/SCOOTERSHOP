# inventory/views/motorcycle_create_view.py

from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy

from inventory.models import Motorcycle, MotorcycleCondition
from inventory.forms import MotorcycleForm
from .motorcycle_form_handler_mixin import MotorcycleFormHandlerMixin


class MotorcycleCreateView(LoginRequiredMixin, UserPassesTestMixin, MotorcycleFormHandlerMixin, CreateView):
    """View for creating a new motorcycle listing."""
    model = Motorcycle
    form_class = MotorcycleForm
    template_name = 'inventory/motorcycle_form.html'
    # success_url is defined by get_success_url

    def test_func(self):
        """Only staff can create motorcycles."""
        return self.request.user.is_staff

    def dispatch(self, request, *args, **kwargs):
        """Ensure base conditions exist before handling the request."""
        conditions_to_create = [
            ('new', 'New'),
            ('used', 'Used'),
            ('demo', 'Demo'),
            ('hire', 'Hire'),
        ]
        for name, display_name in conditions_to_create:
            MotorcycleCondition.objects.get_or_create(
                name=name,
                defaults={'display_name': display_name}
            )
        # Call the parent dispatch method to continue the request flow
        return super().dispatch(request, *args, **kwargs)

    # form_valid is handled by the mixin now, but we can override to add messages
    def form_valid(self, form):
        """Handle form valid and add success message."""
        # The form_valid logic is now largely handled by the mixin.
        # Call the mixin's form_valid which will save and redirect if formset is also valid.
        response = super().form_valid(form)
        # The success message is added within the mixin's form_valid before the super call
        return response


    def get_success_url(self):
        """Redirect to the detail page of the newly created motorcycle."""
        # This will only be called if form_valid (and thus formset validation) succeeded
        return reverse_lazy('inventory:motorcycle-detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_create_view'] = True
        context['page_title'] = 'Add New Motorcycle'
        return context