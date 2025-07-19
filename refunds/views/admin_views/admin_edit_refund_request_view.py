from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.utils import timezone
from core.mixins import AdminRequiredMixin
from refunds.forms.admin_refund_request_form import AdminRefundRequestForm
from refunds.models.RefundRequest import RefundRequest


class AdminEditRefundRequestView(AdminRequiredMixin, View):
    template_name = "refunds/admin_edit_refund_form.html"

    def get(self, request, pk, *args, **kwargs):
        refund_request = get_object_or_404(RefundRequest, pk=pk)
        form = AdminRefundRequestForm(instance=refund_request)

        booking_reference = "N/A"
        if refund_request.service_booking:
            booking_reference = refund_request.service_booking.service_booking_reference
            title = f"Edit Service Refund Request for Booking {booking_reference}"
        elif refund_request.sales_booking:
            booking_reference = refund_request.sales_booking.sales_booking_reference
            title = f"Edit Sales Refund Request for Booking {booking_reference}"
        else:
            title = "Edit Refund Request"

        context = {
            "form": form,
            "title": title,
            "refund_request": refund_request,
            "booking_reference": booking_reference,
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

    def post(self, request, pk, *args, **kwargs):
        refund_request_instance = get_object_or_404(RefundRequest, pk=pk)
        form = AdminRefundRequestForm(request.POST, instance=refund_request_instance)

        if form.is_valid():
            refund_request_instance = form.save(commit=False)

            # Logic for updating status based on admin action
            if refund_request_instance.status == "unverified":
                refund_request_instance.status = "reviewed_pending_approval"
            elif refund_request_instance.status == "pending":
                refund_request_instance.status = "reviewed_pending_approval"

            if (
                refund_request_instance.status
                in ["approved", "refunded", "partially_refunded"]
                and not refund_request_instance.processed_by
            ):
                refund_request_instance.processed_by = request.user
                refund_request_instance.processed_at = timezone.now()

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
                f"Refund Request for booking '{booking_reference_for_msg}' updated successfully! Current Status: {refund_request_instance.get_status_display()}",
            )
            return redirect("refunds:admin_refund_management")
        else:
            messages.error(request, "Please correct the errors below.")
            booking_reference_for_display = "N/A"
            if refund_request_instance.service_booking:
                booking_reference_for_display = (
                    refund_request_instance.service_booking.service_booking_reference
                )
            elif refund_request_instance.sales_booking:
                booking_reference_for_display = (
                    refund_request_instance.sales_booking.sales_booking_reference
                )

            context = {
                "form": form,
                "title": "Edit Refund Request",
                "refund_request": refund_request_instance,
                "booking_reference": booking_reference_for_display,
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
