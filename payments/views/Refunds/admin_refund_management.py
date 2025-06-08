from django.contrib.admin.views.decorators import staff_member_required
from django.views.generic import ListView
from django.utils.decorators import method_decorator
from payments.models import RefundRequest
from django.utils import timezone
from datetime import timedelta
from mailer.utils import send_templated_email
from django.conf import settings

# Import booking and profile models to access their specific fields and types
from hire.models import HireBooking, DriverProfile
from service.models import ServiceBooking, ServiceProfile


@method_decorator(staff_member_required, name='dispatch')
class AdminRefundManagement(ListView):
    """
    View for administrators to manage all RefundRequest instances,
    displaying them in a list with filtering and actions.
    This view is generalized to handle both HireBookings and ServiceBookings.
    """
    model = RefundRequest
    template_name = 'payments/admin_refund_management.html' # Renamed to generic template name
    context_object_name = 'refund_requests'
    paginate_by = 20

    def clean_expired_unverified_refund_requests(self):
        """
        Deletes 'unverified' RefundRequest objects older than 24 hours
        and sends an email notification to the user.
        This method is now generalized to handle both Hire and Service bookings.
        """
        cutoff_time = timezone.now() - timedelta(hours=24)

        expired_requests = RefundRequest.objects.filter(
            status='unverified',
            token_created_at__lt=cutoff_time
        )

        for refund_request in list(expired_requests):
            try:
                recipient_email = refund_request.request_email
                booking_object = None
                customer_profile_object = None
                booking_reference_for_email = "N/A"
                email_template_name = 'emails/user_refund_request_expired_unverified.html' # Default template

                if refund_request.hire_booking:
                    booking_object = refund_request.hire_booking
                    customer_profile_object = refund_request.driver_profile
                    booking_reference_for_email = refund_request.hire_booking.booking_reference
                elif refund_request.service_booking:
                    booking_object = refund_request.service_booking
                    customer_profile_object = refund_request.service_profile
                    booking_reference_for_email = refund_request.service_booking.service_booking_reference

                # Fallback to user email from profile if request_email not set on RefundRequest
                if not recipient_email and customer_profile_object and customer_profile_object.user:
                    recipient_email = customer_profile_object.user.email

                admin_email_context = {
                    'refund_request': refund_request,
                    'admin_email': settings.DEFAULT_FROM_EMAIL,
                    'booking_reference': booking_reference_for_email,
                }

                if recipient_email:
                    send_templated_email(
                        recipient_list=[recipient_email],
                        subject=f"Important: Your Refund Request for Booking {booking_reference_for_email} Has Expired",
                        template_name=email_template_name,
                        context=admin_email_context,
                        booking=booking_object, # Pass generic booking object
                        # Conditionally pass driver/service profile based on type
                        driver_profile=customer_profile_object if isinstance(customer_profile_object, DriverProfile) else None,
                        service_profile=customer_profile_object if isinstance(customer_profile_object, ServiceProfile) else None,
                    )
                else:
                    # If no recipient email found, log or handle silently
                    # print(f"DEBUG: No recipient email for expired refund request {refund_request.pk}")
                    pass

                refund_request.delete()

            except Exception as e:
                # print(f"ERROR: Failed to clean expired unverified refund request {refund_request.pk}: {e}")
                pass # Fail silently as per previous requests if no explicit logging is needed


    def get_queryset(self):
        """
        Overrides get_queryset to perform cleaning of expired unverified refund requests
        before retrieving the queryset for display.
        The queryset now implicitly includes both hire and service bookings
        due to the RefundRequest model's structure.
        """
        self.clean_expired_unverified_refund_requests()

        queryset = super().get_queryset()
        status_filter = self.request.GET.get('status')

        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        return queryset

    def get_context_data(self, **kwargs):
        """
        Adds status choices and current status to the context for filtering.
        """
        context = super().get_context_data(**kwargs)
        context['status_choices'] = RefundRequest.STATUS_CHOICES
        context['current_status'] = self.request.GET.get('status', 'all')
        return context

