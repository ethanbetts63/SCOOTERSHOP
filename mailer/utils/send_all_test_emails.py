import os
import uuid
from django.conf import settings
from mailer.utils.send_templated_email import send_templated_email
from dashboard.models import SiteSettings
from users.tests.test_helpers.model_factories import SuperUserFactory
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
        # Create one unique user for the entire test run
        unique_username = f"admin_test_user_{uuid.uuid4().hex}"
        admin_user = SuperUserFactory(
            email=admin_email,
            username=unique_username
        )

        # Force the sales booking factory to use a unique stock number
        unique_stock_number = f"TEST-{uuid.uuid4().hex[:6].upper()}"
        sales_booking = SalesBookingFactory(
            sales_profile__user=admin_user,
            motorcycle__stock_number=unique_stock_number
        )

        # Create other necessary test objects
        service_booking = ServiceBookingFactory(service_profile__user=admin_user)
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
            enquiry = None
            refund_request = None
            payment = None
            no_data_message = None

            if "service" in template_name:
                booking = service_booking
                profile = booking.service_profile
            elif "sales" in template_name:
                booking = sales_booking
                profile = booking.sales_profile
            elif "enquiry" in template_name:
                enquiry = enquiry_instance
            elif "refund" in template_name:
                refund_request = refund_request_instance
                booking = service_booking
                profile = booking.service_profile
                payment = payment_instance

            context = {
                "booking": booking,
                "profile": profile,
                "user": admin_user,
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
        # Clean up all temporary test data
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