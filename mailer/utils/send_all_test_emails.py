import os
from django.conf import settings
from mailer.utils.send_templated_email import send_templated_email
from dashboard.models import SiteSettings
from users.tests.test_helpers.model_factories import UserFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory
from payments.tests.test_helpers.model_factories import PaymentFactory
from refunds.tests.test_helpers.model_factories import RefundRequestFactory
from core.tests.test_helpers.model_factories import EnquiryFactory


def send_all_test_emails(admin_email):
    template_dir = os.path.join(settings.BASE_DIR, "mailer", "templates")
    service_booking = None
    sales_booking = None
    admin_user = None
    payment_instance = None
    enquiry_instance = None
    refund_request_instance = None

    try:
        service_booking = ServiceBookingFactory()
        sales_booking = SalesBookingFactory()
        admin_user = UserFactory(
            email=admin_email, is_staff=True, is_superuser=True
        )  # Create an admin user for context
        site_settings = SiteSettings.get_settings()
        enquiry_instance = EnquiryFactory()
        payment_instance = PaymentFactory()
        refund_request_instance = RefundRequestFactory(
            service_booking=service_booking, payment=payment_instance
        )

        for template_name in os.listdir(template_dir):
            if not template_name.endswith(".html"):
                continue

            booking = None
            profile = None
            no_data_message = None
            enquiry = None
            refund_request = None
            payment = None

            # Determine context based on template name
            if "service" in template_name:
                if service_booking:
                    booking = service_booking
                    profile = booking.service_profile
                else:
                    no_data_message = "Could not find a sample Service Booking to populate this email."
            elif "sales" in template_name:
                if sales_booking:
                    booking = sales_booking
                    profile = booking.sales_profile
                else:
                    no_data_message = (
                        "Could not find a sample Sales Booking to populate this email."
                    )
            elif "enquiry" in template_name:
                enquiry = enquiry_instance
            elif "refund" in template_name:
                refund_request = refund_request_instance
                booking = service_booking  # Link refund to a booking for context
                profile = (
                    booking.service_profile
                )  # Link refund to a profile for context
                payment = payment_instance

            # Add other general context items
            context = {
                "booking": booking,
                "profile": profile,
                "user": admin_user,  # Use the created admin user
                "is_test_email": True,
                "no_data_message": no_data_message,
                "SITE_DOMAIN": settings.SITE_DOMAIN,
                "SITE_SCHEME": settings.SITE_SCHEME,
                "site_settings": site_settings,
                "enquiry": enquiry,
                "refund_request": refund_request,
                "payment": payment,
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
        if enquiry_instance:
            enquiry_instance.delete()
        if payment_instance:
            payment_instance.delete()
        if refund_request_instance:
            refund_request_instance.delete()


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
