from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from inventory.mixins import AdminRequiredMixin

from inventory.forms import AdminSalesBookingForm
from inventory.models import SalesBooking


class SalesBookingCreateUpdateView(AdminRequiredMixin, View):
    template_name = "inventory/admin_sales_booking_create_update.html"
    form_class = AdminSalesBookingForm

    def get(self, request, pk=None, *args, **kwargs):
        instance = None
        if pk:
            instance = get_object_or_404(SalesBooking, pk=pk)

            form = self.form_class(instance=instance)
        else:
            form = self.form_class()

        context = {
            "form": form,
            "is_edit_mode": bool(pk),
            "current_booking": instance,
            "page_title": "Edit Sales Booking" if pk else "Create Sales Booking",
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        instance = None
        if pk:
            instance = get_object_or_404(SalesBooking, pk=pk)
            form = self.form_class(request.POST, instance=instance)
        else:
            form = self.form_class(request.POST)

        if form.is_valid():
            sales_booking = form.save(commit=False)

            sales_booking.sales_profile = form.cleaned_data["sales_profile"]
            sales_booking.motorcycle = form.cleaned_data["motorcycle"]

            sales_booking.save()

            if pk:
                messages.success(
                    request,
                    f"Sales Booking '{sales_booking.sales_booking_reference}' updated successfully.",
                )
            else:
                messages.success(
                    request,
                    f"Sales Booking '{sales_booking.sales_booking_reference}' created successfully.",
                )
            return redirect(reverse("inventory:sales_bookings_management"))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                "form": form,
                "is_edit_mode": bool(pk),
                "current_booking": instance,
                "page_title": "Edit Sales Booking" if pk else "Create Sales Booking",
            }
            return render(request, self.template_name, context)
