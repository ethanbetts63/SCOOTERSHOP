from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.utils import timezone
from core.mixins import AdminRequiredMixin
from refunds.forms.admin_refund_request_form import AdminRefundRequestForm
from refunds.models.RefundRequest import RefundRequest


class AdminAddEditRefundRequestView(AdminRequiredMixin, View):
    template_name = "payments/admin_refund_form.html"

    def get(self, request, pk=None, *args, **kwargs):

        refund_request = None
        booking_reference = "N/A"

        if pk:
            refund_request = get_object_or_404(RefundRequest, pk=pk)
            form = AdminRefundRequestForm(instance=refund_request)
            title = "Edit Refund Request"

            if refund_request.service_booking:
                booking_reference = (
                    refund_request.service_booking.service_booking_reference
                )
                title = f"Edit Service Refund Request for Booking {booking_reference}"
            elif refund_request.sales_booking:
                booking_reference = refund_request.sales_booking.sales_booking_reference
                title = f"Edit Sales Refund Request for Booking {booking_reference}"
        else:
            form = AdminRefundRequestForm()
            title = "Create New Refund Request"

        context = {
            "form": form,
            "title": title,
            "refund_request": refund_request,
            "booking_reference": booking_reference,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):

        refund_request_instance = None
        if pk:
            refund_request_instance = get_object_or_404(RefundRequest, pk=pk)
            form = AdminRefundRequestForm(
                request.POST, instance=refund_request_instance
            )
        else:
            form = AdminRefundRequestForm(request.POST)

        admin_management_redirect_url = "payments:admin_refund_management"

        if form.is_valid():
            refund_request_instance = form.save(commit=False)

            refund_request_instance.is_admin_initiated = True

            if not pk:

                refund_request_instance.status = "reviewed_pending_approval"
            elif refund_request_instance.status == "unverified":
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
                f"Refund Request for booking '{booking_reference_for_msg}' saved successfully! Current Status: {refund_request_instance.get_status_display()}",
            )
            return redirect(admin_management_redirect_url)
        else:
            messages.error(request, "Please correct the errors below.")
            title = "Edit Refund Request" if pk else "Create New Refund Request"
            booking_reference_for_display = "N/A"
            if refund_request_instance and refund_request_instance.service_booking:
                booking_reference_for_display = (
                    refund_request_instance.service_booking.service_booking_reference
                )
            elif refund_request_instance and refund_request_instance.sales_booking:
                booking_reference_for_display = (
                    refund_request_instance.sales_booking.sales_booking_reference
                )

            context = {
                "form": form,
                "title": title,
                "refund_request": refund_request_instance,
                "booking_reference": booking_reference_for_display,
            }
            return render(request, self.template_name, context)
