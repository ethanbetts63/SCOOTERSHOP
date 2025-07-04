from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from inventory.models import BlockedSalesDate
from inventory.forms import AdminBlockedSalesDateForm
from inventory.mixins import AdminRequiredMixin


class BlockedSalesDateManagementView(AdminRequiredMixin, View):
    template_name = "inventory/admin_blocked_sales_date_management.html"

    def get(self, request, *args, **kwargs):
        form = AdminBlockedSalesDateForm()
        blocked_dates = BlockedSalesDate.objects.all().order_by("start_date")
        context = {
            "form": form,
            "blocked_sales_dates": blocked_dates,
            "page_title": "Blocked Sales Dates Management",
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        if "add_blocked_sales_date_submit" in request.POST:
            form = AdminBlockedSalesDateForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Blocked sales date added successfully.")
                return redirect("inventory:blocked_sales_date_management")
            else:
                messages.error(
                    request, "There was an error adding the blocked sales date."
                )
        else:
            form = AdminBlockedSalesDateForm()

        blocked_dates = BlockedSalesDate.objects.all().order_by("start_date")
        context = {
            "form": form,
            "blocked_sales_dates": blocked_dates,
            "page_title": "Blocked Sales Dates Management",
        }
        return render(request, self.template_name, context)