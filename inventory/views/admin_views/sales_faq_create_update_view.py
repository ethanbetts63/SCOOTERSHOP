from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from inventory.mixins import AdminRequiredMixin
from inventory.forms import AdminSalesfaqForm
from inventory.models import Salesfaq


class SalesfaqCreateUpdateView(AdminRequiredMixin, View):
    template_name = "inventory/admin_sales_faq_create_update.html"
    form_class = AdminSalesfaqForm

    def get(self, request, pk=None, *args, **kwargs):
        if pk:
            instance = get_object_or_404(Salesfaq, pk=pk)
            form = self.form_class(instance=instance)
        else:
            instance = None
            form = self.form_class()

        context = {
            "form": form,
            "is_edit_mode": bool(pk),
            "page_title": "Edit Sales faq" if pk else "Create Sales faq",
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        if pk:
            instance = get_object_or_404(Salesfaq, pk=pk)
            form = self.form_class(request.POST, instance=instance)
        else:
            instance = None
            form = self.form_class(request.POST)

        if form.is_valid():
            faq = form.save()
            if pk:
                messages.success(
                    request, f"Sales faq '{faq.question[:50]}...' updated successfully."
                )
            else:
                messages.success(
                    request, f"Sales faq '{faq.question[:50]}...' created successfully."
                )
            return redirect(reverse("inventory:sales_faq_management"))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                "form": form,
                "is_edit_mode": bool(pk),
                "page_title": "Edit Sales faq" if pk else "Create Sales faq",
            }
            return render(request, self.template_name, context)
