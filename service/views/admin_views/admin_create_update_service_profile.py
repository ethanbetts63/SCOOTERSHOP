from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from service.mixins import AdminRequiredMixin

from service.forms import AdminServiceProfileForm
from service.models import ServiceProfile


class ServiceProfileCreateUpdateView(AdminRequiredMixin, View):
    template_name = "service/admin_service_profile_create_update.html"
    form_class = AdminServiceProfileForm

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get(self, request, pk=None, *args, **kwargs):
        instance = None
        if pk:
            instance = get_object_or_404(ServiceProfile, pk=pk)
            form = self.form_class(instance=instance)
        else:
            form = self.form_class()

        context = {"form": form, "is_edit_mode": bool(pk), "current_profile": instance}
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        instance = None
        if pk:
            instance = get_object_or_404(ServiceProfile, pk=pk)
            form = self.form_class(request.POST, instance=instance)
        else:
            form = self.form_class(request.POST)

        if form.is_valid():
            service_profile = form.save()
            if pk:
                messages.success(
                    request,
                    f"Service Profile for '{service_profile.name}' updated successfully.",
                )
            else:
                messages.success(
                    request,
                    f"Service Profile for '{service_profile.name}' created successfully.",
                )

            return redirect(reverse("service:admin_service_profiles"))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                "form": form,
                "is_edit_mode": bool(pk),
                "current_profile": instance,
            }
            return render(request, self.template_name, context)
