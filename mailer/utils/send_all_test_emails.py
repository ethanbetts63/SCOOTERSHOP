import os
import random
from django.conf import settings
from mailer.utils.send_templated_email import send_templated_email
from service.models import ServiceBooking
from inventory.models import SalesBooking
from users.models import User
from dashboard.models import SiteSettings
from mailer.tests.test_helpers.model_factories import ServiceBookingFactory, SalesBookingFactory, UserFactory

def send_all_test_emails(admin_email):
    template_dir = os.path.join(settings.BASE_DIR, 'mailer', 'templates')

    # Create instances using factories
    service_booking = None
    sales_booking = None
    admin_user = None

    try:
        service_booking = ServiceBookingFactory()
        sales_booking = SalesBookingFactory()
        admin_user = UserFactory(email=admin_email, is_staff=True, is_superuser=True) # Create an admin user for context
        site_settings = SiteSettings.get_settings()

        for template_name in os.listdir(template_dir):
            if not template_name.endswith('.html'):
                continue

            booking = None
            profile = None
            no_data_message = None

            # Determine context based on template name
            if 'service' in template_name:
                if service_booking:
                    booking = service_booking
                    profile = booking.service_profile
                else:
                    no_data_message = "Could not find a sample Service Booking to populate this email."
            elif 'sales' in template_name:
                if sales_booking:
                    booking = sales_booking
                    profile = booking.sales_profile
                else:
                    no_data_message = "Could not find a sample Sales Booking to populate this email."
            
            # Add other general context items
            context = {
                'booking': booking,
                'profile': profile,
                'user': admin_user, # Use the created admin user
                'is_test_email': True,
                'no_data_message': no_data_message,
                'SITE_DOMAIN': settings.SITE_DOMAIN,
                'SITE_SCHEME': settings.SITE_SCHEME,
                'site_settings': site_settings
            }

            send_templated_email(
                recipient_list=[admin_email],
                subject=f"Test Email: {template_name}",
                template_name=template_name,
                context=context,
                booking=booking,
                profile=profile,
            )
    finally:
        # Clean up created instances
        if service_booking:
            service_booking.delete()
        if sales_booking:
            sales_booking.delete()
        if admin_user:
            admin_user.delete()

# def send_all_test_emails(admin_email):
#     """
#     Sends a test version of the admin_refund_request_approved.html email template.
#     """
#     # Assuming refund requests are tied to ServiceBookings or SalesBookings
#     # For this test, we'll use a ServiceBooking as a placeholder for context.
#     booking = ServiceBooking.objects.order_by("?").first()
#     admin_user = User.objects.filter(email=admin_email).first()
#     site_settings = SiteSettings.get_settings()

#     context = {
#         'booking': booking,
#         'profile': booking.service_profile if booking else None,
#         'user': admin_user, # The admin user receiving the email
#         'is_test_email': True,
#         'no_data_message': None,
#         'SITE_DOMAIN': settings.SITE_DOMAIN,
#         'SITE_SCHEME': settings.SITE_SCHEME,
#         'site_settings': site_settings,
#         'refund_amount': "123.45", # Example refund amount
#         'refund_reason': "Test refund reason for approved request.",
#         'refund_status': "Approved",
#     }

#     if not booking:
#         context['no_data_message'] = "Could not find a sample Service Booking to populate this email. Some fields may be empty."

#     send_templated_email(
#         recipient_list=[admin_email],
#         subject="Test Email: Admin Refund Request Approved",
#         template_name="admin_refund_request_approved.html",
#         context=context,
#         booking=booking,
#         profile=booking.service_profile if booking else None,
#     )
