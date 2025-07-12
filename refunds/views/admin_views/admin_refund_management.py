from django.views.generic import ListView
from django.utils import timezone
from datetime import timedelta
from mailer.utils import send_templated_email
from django.conf import settings
from core.mixins import AdminRequiredMixin
from refunds.models import RefundRequest
from service.models import ServiceProfile
from inventory.models import SalesProfile


class AdminRefundManagement(AdminRequiredMixin, ListView):
    model = RefundRequest
    template_name = "payments/admin_refund_management.html"
    context_object_name = "refund_requests"
    paginate_by = 20

    def clean_expired_unverified_refund_requests(self):
        cutoff_time = timezone.now() - timedelta(hours=24)

        expired_requests = RefundRequest.objects.filter(
            status="unverified", token_created_at__lt=cutoff_time
        )

        for refund_request in list(expired_requests):
            try:
                recipient_email = refund_request.request_email
                booking_object = None
                customer_profile_object = None
                booking_reference_for_email = "N/A"
                email_template_name = (
                    "emails/user_refund_request_expired_unverified.html"
                )

                if refund_request.service_booking:
                    booking_object = refund_request.service_booking
                    customer_profile_object = refund_request.service_profile
                    booking_reference_for_email = (
                        refund_request.service_booking.service_booking_reference
                    )
                elif refund_request.sales_booking:
                    booking_object = refund_request.sales_booking
                    customer_profile_object = refund_request.sales_profile
                    booking_reference_for_email = (
                        refund_request.sales_booking.sales_booking_reference
                    )

                if (
                    not recipient_email
                    and customer_profile_object
                    and customer_profile_object.user
                ):
                    recipient_email = customer_profile_object.user.email

                admin_email_context = {
                    "refund_request": refund_request,
                    "admin_email": settings.DEFAULT_FROM_EMAIL,
                    "booking_reference": booking_reference_for_email,
                }

                if recipient_email:
                    user_email_context = {
                        "refund_request": refund_request,
                        "booking_reference": booking_reference_for_email,
                        "admin_email": getattr(
                            settings, "ADMIN_EMAIL", settings.DEFAULT_FROM_EMAIL
                        ),
                    }
                    send_templated_email(
                        recipient_list=[recipient_email],
                        subject=f"Important: Your Refund Request for Booking {booking_reference_for_email} Has Expired",
                        template_name="user_refund_request_expired_unverified.html",
                        context=user_email_context,
                        booking=booking_object,
                        service_profile=(
                            customer_profile_object
                            if isinstance(customer_profile_object, ServiceProfile)
                            else None
                        ),
                        sales_profile=(
                            customer_profile_object
                            if isinstance(customer_profile_object, SalesProfile)
                            else None
                        ),
                    )
                else:
                    pass
                refund_request.delete()

            except Exception:
                pass

    def get_queryset(self):
        self.clean_expired_unverified_refund_requests()

        queryset = super().get_queryset()
        status_filter = self.request.GET.get("status")

        if status_filter and status_filter != "all":
            queryset = queryset.filter(status=status_filter)
        return queryset

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context["status_choices"] = RefundRequest.STATUS_CHOICES
        context["current_status"] = self.request.GET.get("status", "all")
        return context
