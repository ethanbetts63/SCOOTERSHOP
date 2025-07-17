from service.mixins import AdminRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django.contrib import messages
from django.forms import ValidationError

from service.models import ServiceSettings
from service.forms import ServiceBookingSettingsForm


class ServiceSettingsView(AdminRequiredMixin, UpdateView):
    model = ServiceSettings
    form_class = ServiceBookingSettingsForm
    template_name = "service/service_settings.html"
    success_url = reverse_lazy("service:service_settings")

    def get_object(self, queryset=None):
        obj, created = ServiceSettings.objects.get_or_create(pk=1)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Service settings updated successfully!")
            return response
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(
            self.request,
            "There was an error updating service settings. Please correct the errors below.",
        )
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        if "service_settings_submit" in request.POST:
            self.object = self.get_object()
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)

        return super().post(request, *args, **kwargs)
