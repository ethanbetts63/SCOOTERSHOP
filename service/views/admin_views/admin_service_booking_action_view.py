from service.mixins import AdminRequiredMixin
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django.contrib import messages
from service.models import ServiceBooking
from service.forms import ServiceBookingActionForm
from service.utils.confirm_service_booking import confirm_service_booking
from service.utils.reject_service_booking import reject_service_booking
from django.shortcuts import redirect


class ServiceBookingActionView(AdminRequiredMixin, FormView):
    template_name = "service/admin_service_booking_action.html"
    form_class = ServiceBookingActionForm
    success_url = reverse_lazy("service:service_booking_management")

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_initial(self):
        initial = super().get_initial()
        service_booking_id = self.kwargs["pk"]
        action_type = self.kwargs["action_type"]

        initial["service_booking_id"] = service_booking_id
        initial["action"] = action_type

        if action_type == "reject":
            try:
                booking = ServiceBooking.objects.get(pk=service_booking_id)
                if booking.payment_status == "deposit_paid" and booking.amount_paid:
                    initial["refund_amount"] = booking.amount_paid
            except ServiceBooking.DoesNotExist:
                pass

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service_booking_id = self.kwargs["pk"]
        action_type = self.kwargs["action_type"]

        try:
            booking = ServiceBooking.objects.get(pk=service_booking_id)
            context["booking"] = booking
            if action_type == "confirm":
                context["page_title"] = (
                    f"Confirm Service Booking: {booking.service_booking_reference}"
                )
                context["action_display"] = "Confirm"
            elif action_type == "reject":
                context["page_title"] = (
                    f"Reject Service Booking: {booking.service_booking_reference}"
                )
                context["action_display"] = "Reject"
            else:
                context["page_title"] = "Invalid Service Booking Action"
                context["action_display"] = "Invalid"
        except ServiceBooking.DoesNotExist:
            messages.error(self.request, "Service Booking not found.")
            context["page_title"] = "Service Booking Not Found"
            context["booking"] = None

        context["action_type"] = action_type
        return context

    def dispatch(self, request, *args, **kwargs):
        try:
            ServiceBooking.objects.get(pk=self.kwargs["pk"])
        except ServiceBooking.DoesNotExist:
            messages.error(request, "The specified service booking does not exist.")
            return redirect("service:service_booking_management")

        action_type = self.kwargs.get("action_type")
        if action_type not in ["confirm", "reject"]:
            messages.error(request, "Invalid action type specified.")
            return redirect("service:service_booking_management")

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        service_booking_id = form.cleaned_data["service_booking_id"]
        action = form.cleaned_data["action"]

        if action == "confirm":
            result = confirm_service_booking(
                service_booking_id=service_booking_id,
                message=form.cleaned_data.get("message"),
                send_notification=form.cleaned_data.get("send_notification", False),
            )
            self.success_url = reverse_lazy("service:service_booking_management")

        elif action == "reject":
            form_data_for_utility = {
                "message": form.cleaned_data.get("message"),
                "send_notification": form.cleaned_data.get("send_notification", False),
                "initiate_refund": form.cleaned_data.get("initiate_refund", False),
                "refund_amount": form.cleaned_data.get("refund_amount"),
            }
            result = reject_service_booking(
                service_booking_id=service_booking_id,
                requesting_user=self.request.user,
                form_data=form_data_for_utility,
                send_notification=form_data_for_utility["send_notification"],
            )

            if result["success"] and "refund_request_pk" in result:
                messages.success(self.request, result["message"])

                self.success_url = reverse_lazy(
                    "refunds:initiate_refund_process",
                    kwargs={"pk": result["refund_request_pk"]},
                )
                return super().form_valid(form)
            else:
                self.success_url = reverse_lazy("service:service_booking_management")

        else:
            messages.error(self.request, "Invalid action type provided.")
            return self.form_invalid(form)

        if result["success"]:
            messages.success(self.request, result["message"])
        else:
            messages.error(self.request, result["message"])
            return self.form_invalid(form)

        return super().form_valid(form)
