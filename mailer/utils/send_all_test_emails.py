import os
import random
from django.conf import settings
from mailer.utils.send_templated_email import send_templated_email
from service.models import ServiceBooking
from inventory.models import SalesBooking
from users.models import User
from dashboard.models import SiteSettings

def send_all_test_emails(admin_email):
    """
    Sends a test version of every email template to the specified admin email.
    It tries to find a random ServiceBooking and SalesBooking to populate
    the templates with realistic data.
    """
    template_dir = os.path.join(settings.BASE_DIR, 'mailer', 'templates')

    # Get one random instance for service and sales to use for all templates
    service_booking = ServiceBooking.objects.order_by("?").first()
    sales_booking = SalesBooking.objects.order_by("?").first()
    admin_user = User.objects.filter(email=admin_email).first()
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
            'user': profile.user if profile else admin_user,
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
