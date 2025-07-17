from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from inventory.mixins import AdminRequiredMixin
from service.forms import AdminServicefaqForm
from service.models import Servicefaq


class ServicefaqCreateUpdateView(AdminRequiredMixin, View):
    template_name = "service/admin_service_faq_create_update.html"
    form_class = AdminServicefaqForm

    def get(self, request, pk=None, *args, **kwargs):
        if pk:
            instance = get_object_or_404(Servicefaq, pk=pk)
            form = self.form_class(instance=instance)
            page_title = "Edit Service faq"
        else:
            instance = None
            form = self.form_class()
            page_title = "Create Service faq"

        context = {"form": form, "is_edit_mode": bool(pk), "page_title": page_title}
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        if pk:
            instance = get_object_or_404(Servicefaq, pk=pk)
            form = self.form_class(request.POST, instance=instance)
        else:
            instance = None
            form = self.form_class(request.POST)

        if form.is_valid():
            faq = form.save()
            if pk:
                messages.success(
                    request,
                    f"Service faq '{faq.question[:50]}...' updated successfully.",
                )
            else:
                messages.success(
                    request,
                    f"Service faq '{faq.question[:50]}...' created successfully.",
                )
            return redirect(reverse("service:service_faq_management"))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                "form": form,
                "is_edit_mode": bool(pk),
                "page_title": "Edit Service faq" if pk else "Create Service faq",
            }
            return render(request, self.template_name, context)
