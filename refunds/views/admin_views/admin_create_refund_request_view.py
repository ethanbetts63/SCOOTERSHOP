from django.urls import reverse
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.utils import timezone
from core.mixins import AdminRequiredMixin
from refunds.forms.admin_refund_request_form import AdminRefundRequestForm
from refunds.models.RefundRequest import RefundRequest


class AdminCreateRefundRequestView(AdminRequiredMixin, View):
    template_name = "refunds/admin_create_refund_form.html"

    def get(self, request, *args, **kwargs):
        form = AdminRefundRequestForm()
        context = {
            "form": form,
            "title": "Create New Refund Request",
            "service_booking_details_url": reverse(
                "service:admin_api_get_service_booking_details", args=[0]
            ),
            "sales_booking_details_url": reverse(
                "inventory:api_sales_booking_details", args=[0]
            ),
            "search_sales_bookings_url": reverse(
                "inventory:admin_api_search_sales_bookings"
            ),
            "search_service_bookings_url": reverse("service:admin_api_search_bookings"),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = AdminRefundRequestForm(request.POST)

        if form.is_valid():
            refund_request_instance = form.save(commit=False)
            refund_request_instance.is_admin_initiated = True
            refund_request_instance.status = "reviewed_pending_approval"
            refund_request_instance.save()

            booking_reference_for_msg = "N/A"
            if refund_request_instance.service_booking:
                booking_reference_for_msg = (
                    refund_request_instance.service_booking.service_booking_reference
                )
            elif refund_request_instance.sales_booking:
                booking_reference_for_msg = (
                    refund_request_instance.sales_booking.sales_booking_reference
                )

            messages.success(
                request,
                f"Refund Request for booking '{booking_reference_for_msg}' created successfully! Current Status: {refund_request_instance.get_status_display()}",
            )
            return redirect("refunds:admin_refund_management")
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                "form": form,
                "title": "Create New Refund Request",
                "service_booking_details_url": reverse(
                    "service:admin_api_get_service_booking_details", args=[0]
                ),
                "sales_booking_details_url": reverse(
                    "inventory:api_sales_booking_details", args=[0]
                ),
                "search_sales_bookings_url": reverse(
                    "inventory:admin_api_search_sales_bookings"
                ),
                "search_service_bookings_url": reverse("service:admin_api_search_bookings"),
            }
            return render(request, self.template_name, context)
