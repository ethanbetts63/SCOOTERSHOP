from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from service.models import BlockedServiceDate
from service.forms import BlockedServiceDateForm


class BlockedServiceDateManagementView(View):

    template_name = "service/blocked_service_dates_management.html"
    form_class = BlockedServiceDateForm

    def get(self, request, *args, **kwargs):

        form = self.form_class()
        blocked_service_dates = BlockedServiceDate.objects.all()

        context = {
            "page_title": "Blocked Service Dates Management",
            "form": form,
            "blocked_dates": blocked_service_dates,
            "active_tab": "service_booking",
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):

        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Blocked service date added successfully!")

            return redirect("service:blocked_service_dates_management")
        else:
            messages.error(
                request, "Error adding blocked service date. Please check the form."
            )

            blocked_service_dates = BlockedServiceDate.objects.all()
            context = {
                "page_title": "Blocked Service Dates Management",
                "form": form,
                "blocked_dates": blocked_service_dates,
                "active_tab": "service_booking",
            }
            return render(request, self.template_name, context)
