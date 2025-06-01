# payments/views/HireRefunds/admin_hire_refund_management.py
from django.contrib.admin.views.decorators import staff_member_required
from django.views.generic import ListView
from django.utils.decorators import method_decorator
from payments.models import HireRefundRequest
from django.utils import timezone # Import timezone for date calculations
from datetime import timedelta # Import timedelta for time calculations
from mailer.utils import send_templated_email # Import the email utility
from django.conf import settings # Import settings to get DEFAULT_FROM_EMAIL

# Removed logging import as per request.

@method_decorator(staff_member_required, name='dispatch')
class AdminHireRefundManagement(ListView):
    model = HireRefundRequest
    template_name = 'payments/admin_hire_refund_management.html'
    context_object_name = 'refund_requests'
    paginate_by = 20

    # Removed dispatch override as per request to move cleaning to get_queryset.

    def clean_expired_unverified_refund_requests(self):
        """
        Deletes 'unverified' HireRefundRequest objects older than 24 hours
        and sends an email notification to the user.
        Replaced logging statements with print debugs as requested.
        """
        # Calculate the cutoff time (24 hours ago from now)
        cutoff_time = timezone.now() - timedelta(hours=24)

        # Get expired unverified refund requests
        expired_requests = HireRefundRequest.objects.filter(
            status='unverified',
            token_created_at__lt=cutoff_time
        )

        print(f"DEBUG: Checking for expired unverified refund requests older than {cutoff_time}")

        for refund_request in list(expired_requests): # Convert to list to avoid issues during deletion
            try:
                # Prepare context for the email
                admin_email_context = {
                    'refund_request': refund_request,
                    'admin_email': settings.DEFAULT_FROM_EMAIL, # Use the default from email as admin contact
                }

                # Determine recipient email
                recipient_email = refund_request.request_email
                if not recipient_email and refund_request.driver_profile and refund_request.driver_profile.user:
                    recipient_email = refund_request.driver_profile.user.email

                if recipient_email:
                    # Send email notification
                    send_templated_email(
                        recipient_list=[recipient_email],
                        subject=f"Important: Your Refund Request for Booking {refund_request.hire_booking.booking_reference} Has Expired",
                        template_name='emails/user_refund_request_expired_unverified.html', # Path to the new template
                        context=admin_email_context,
                        driver_profile=refund_request.driver_profile,
                        booking=refund_request.hire_booking
                    )
                    print(f"DEBUG: Sent expiration email for refund request {refund_request.pk} to {recipient_email}")
                else:
                    print(f"DEBUG: Could not send expiration email for refund request {refund_request.pk}: no recipient email found.")

                # Delete the expired request
                refund_request.delete()
                print(f"DEBUG: Deleted expired unverified refund request: {refund_request.pk}")

            except Exception as e:
                print(f"ERROR: Error processing expired refund request {refund_request.pk}: {e}")


    def get_queryset(self):
        """
        Overrides get_queryset to perform cleaning of expired unverified refund requests
        before retrieving the queryset for display.
        """
        # Call the cleaning mechanism here as requested
        self.clean_expired_unverified_refund_requests()

        queryset = super().get_queryset()
        status_filter = self.request.GET.get('status')

        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = HireRefundRequest.STATUS_CHOICES
        context['current_status'] = self.request.GET.get('status', 'all')
        return context
