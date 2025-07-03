from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from service.mixins import AdminRequiredMixin

from service.forms import AdminServiceTypeForm
from service.models import ServiceType


class ServiceTypeCreateUpdateView(AdminRequiredMixin, View):

    template_name = "service/admin_service_type_create_update.html"
    form_class = AdminServiceTypeForm

    def test_func(self):

        return self.request.user.is_staff or self.request.user.is_superuser

    def get(self, request, pk=None, *args, **kwargs):

        instance = None
        if pk:

            instance = get_object_or_404(ServiceType, pk=pk)
            form = self.form_class(instance=instance)
        else:

            form = self.form_class()

        context = {
            "form": form,
            "is_edit_mode": bool(pk),
            "current_service_type": instance,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):

        instance = None
        if pk:
            instance = get_object_or_404(ServiceType, pk=pk)
            form = self.form_class(request.POST, request.FILES, instance=instance)
        else:
            form = self.form_class(request.POST, request.FILES)

        if form.is_valid():
            service_type = form.save()
            if pk:
                messages.success(
                    request, f"Service Type '{service_type.name}' updated successfully."
                )
            else:
                messages.success(
                    request, f"Service Type '{service_type.name}' created successfully."
                )

            return redirect(reverse("service:service_types_management"))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                "form": form,
                "is_edit_mode": bool(pk),
                "current_service_type": instance,
            }
            return render(request, self.template_name, context)
