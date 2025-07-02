from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django.contrib import messages
from django.forms import ValidationError
from inventory.mixins import AdminRequiredMixin

from inventory.models import InventorySettings
from inventory.forms.admin_inventory_settings_form import InventorySettingsForm


class InventorySettingsView(AdminRequiredMixin, UpdateView):
    model = InventorySettings
    form_class = InventorySettingsForm
    template_name = "inventory/admin_inventory_settings.html"
    success_url = reverse_lazy("inventory:inventory_settings")

    def get_object(self, queryset=None):
        obj, created = InventorySettings.objects.get_or_create(pk=1)
        return obj

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Inventory settings updated successfully!")
            return response
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(
            self.request,
            "There was an error updating inventory settings. Please correct the errors below.",
        )
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        if "inventory_settings_submit" in request.POST:
            self.object = self.get_object()
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)

        return super().post(request, *args, **kwargs)
