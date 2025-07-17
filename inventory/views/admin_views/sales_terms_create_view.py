from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django.contrib import messages

from inventory.mixins import AdminRequiredMixin
from inventory.forms import AdminSalesTermsForm


class SalesTermsCreateView(AdminRequiredMixin, View):
    template_name = "inventory/admin_sales_terms_create.html"
    form_class = AdminSalesTermsForm

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        context = {
            "form": form,
            "page_title": "Create New Terms & Conditions Version",
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            terms_version = form.save(commit=False)

            terms_version.is_active = True
            terms_version.save()

            messages.success(
                request,
                f"New Terms & Conditions Version {terms_version.version_number} created successfully and set as active.",
            )
            return redirect(reverse("inventory:terms_and_conditions_management"))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                "form": form,
                "page_title": "Create New Terms & Conditions Version",
            }
            return render(request, self.template_name, context)
