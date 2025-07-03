from inventory.mixins import AdminRequiredMixin
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django.contrib import messages
from inventory.models import SalesBooking
from inventory.forms import SalesBookingActionForm
from inventory.utils.confirm_sales_booking import confirm_sales_booking
from inventory.utils.reject_sales_booking import reject_sales_booking
from django.contrib.auth.mixins import LoginRequiredMixin


class SalesBookingActionView(AdminRequiredMixin, FormView):
    template_name = "inventory/admin_sales_booking_action.html"
    form_class = SalesBookingActionForm
    success_url = reverse_lazy("inventory:sales_bookings_management")

    def get_initial(self):
        initial = super().get_initial()
        sales_booking_id = self.kwargs["pk"]
        action_type = self.kwargs["action_type"]

        initial["sales_booking_id"] = sales_booking_id
        initial["action"] = action_type

        if action_type == "reject":
            try:
                booking = SalesBooking.objects.get(pk=sales_booking_id)
                if booking.payment_status == "deposit_paid" and booking.amount_paid:
                    initial["refund_amount"] = booking.amount_paid
            except SalesBooking.DoesNotExist:
                pass

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sales_booking_id = self.kwargs["pk"]
        action_type = self.kwargs["action_type"]

        try:
            booking = SalesBooking.objects.get(pk=sales_booking_id)
            context["booking"] = booking
            if action_type == "confirm":
                context["page_title"] = (
                    f"Confirm Sales Booking: {booking.sales_booking_reference}"
                )
                context["action_display"] = "Confirm"
            elif action_type == "reject":
                context["page_title"] = (
                    f"Reject Sales Booking: {booking.sales_booking_reference}"
                )
                context["action_display"] = "Reject"
            else:
                context["page_title"] = "Invalid Sales Booking Action"
                context["action_display"] = "Invalid"
        except SalesBooking.DoesNotExist:
            messages.error(self.request, "Sales Booking not found.")
            context["page_title"] = "Sales Booking Not Found"
            context["booking"] = None

        context["action_type"] = action_type
        return context

    def dispatch(self, request, *args, **kwargs):
        try:
            SalesBooking.objects.get(pk=self.kwargs["pk"])
        except SalesBooking.DoesNotExist:
            messages.error(request, "The specified sales booking does not exist.")
            return self.handle_no_permission()

        action_type = self.kwargs.get("action_type")
        if action_type not in ["confirm", "reject"]:
            messages.error(request, "Invalid action type specified.")
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        sales_booking_id = form.cleaned_data["sales_booking_id"]
        action = form.cleaned_data["action"]

        form_data_for_utility = {
            "message": form.cleaned_data.get("message"),
            "send_notification": form.cleaned_data.get("send_notification", False),
            "initiate_refund": form.cleaned_data.get("initiate_refund", False),
            "refund_amount": form.cleaned_data.get("refund_amount"),
        }

        if action == "confirm":
            result = confirm_sales_booking(
                sales_booking_id=sales_booking_id,
                requesting_user=self.request.user,
                form_data=form_data_for_utility,
                send_notification=form_data_for_utility["send_notification"],
            )
            self.success_url = reverse_lazy("inventory:sales_bookings_management")

        elif action == "reject":
            result = reject_sales_booking(
                sales_booking_id=sales_booking_id,
                requesting_user=self.request.user,
                form_data=form_data_for_utility,
                send_notification=form_data_for_utility["send_notification"],
            )

            if result["success"] and "refund_request_pk" in result:
                messages.success(self.request, result["message"])

                self.success_url = reverse_lazy(
                    "payments:initiate_refund_process",
                    kwargs={"pk": result["refund_request_pk"]},
                )
                return super().form_valid(form)
            else:
                self.success_url = reverse_lazy("inventory:sales_bookings_management")

        else:
            messages.error(self.request, "Invalid action type provided.")
            return self.form_invalid(form)

        if result["success"]:
            messages.success(self.request, result["message"])
        else:
            messages.error(self.request, result["message"])
            if not ("refund_request_pk" in result and result["success"]):
                return self.form_invalid(form)

        return super().form_valid(form)
