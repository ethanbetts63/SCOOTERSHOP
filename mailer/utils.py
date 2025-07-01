from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.db import transaction
import logging
import re
from django.utils import timezone
from .models import EmailLog
from hire.models import HireBooking, DriverProfile
from service.models import ServiceBooking, ServiceProfile
from inventory.models import SalesBooking, SalesProfile

logger = logging.getLogger(__name__)

def send_templated_email(
    recipient_list,
    subject,
    template_name,
    context,
    booking,
    profile, # The profile object is now a primary argument
    from_email=None,
):
    if not recipient_list:
        return False

    sender_email = from_email if from_email else settings.DEFAULT_FROM_EMAIL

    # --- New Simplified Logic ---
    # Intelligently determine user and specific profile/booking types from the generic objects passed in.
    user = getattr(profile, 'user', None)

    driver_profile = profile if isinstance(profile, DriverProfile) else None
    service_profile = profile if isinstance(profile, ServiceProfile) else None
    sales_profile = profile if isinstance(profile, SalesProfile) else None

    hire_booking_obj = booking if isinstance(booking, HireBooking) else None
    service_booking_obj = booking if isinstance(booking, ServiceBooking) else None
    sales_booking_obj = booking if isinstance(booking, SalesBooking) else None
    
    # Ensure context has all necessary objects for the template to render correctly.
    context['booking'] = booking
    context['profile'] = profile
    context['user'] = user
    # --- End of New Logic ---

    try:
        html_content = render_to_string(template_name, context)
        text_content_prep = re.sub(r'<br\s*/?>', '\n', html_content)
        text_content_prep = re.sub(r'</p>', '\n\n', text_content_prep)
        text_content_prep = re.sub(r'</(div|h[1-6]|ul|ol|li)>', '\n', text_content_prep)
        text_content_prep = re.sub(r'<(p|div|h[1-6]|ul|ol|li)[^>]*?>', '', text_content_prep)
        text_content = strip_tags(text_content_prep).strip()

    except Exception as e:
        EmailLog.objects.create(
            sender=sender_email, recipient=", ".join(recipient_list), subject=subject,
            body=f"Error rendering template: {template_name}.", status='FAILED',
            error_message=f"Template rendering failed: {e}", user=user,
            driver_profile=driver_profile, service_profile=service_profile,
            sales_profile=sales_profile, booking=hire_booking_obj,
            service_booking=service_booking_obj, sales_booking=sales_booking_obj,
        )
        return False

    email_status = 'PENDING'
    error_msg = None

    try:
        msg = EmailMultiAlternatives(subject, text_content, sender_email, recipient_list)
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        email_status = 'SENT'
        success = True
    except Exception as e:
        email_status = 'FAILED'
        error_msg = str(e)
        success = False
    finally:
        try:
            with transaction.atomic():
                EmailLog.objects.create(
                    timestamp=timezone.now(), sender=sender_email,
                    recipient=", ".join(recipient_list), subject=subject,
                    body=html_content, status=email_status, error_message=error_msg,
                    user=user, driver_profile=driver_profile,
                    service_profile=service_profile, sales_profile=sales_profile,
                    booking=hire_booking_obj, service_booking=service_booking_obj,
                    sales_booking=sales_booking_obj,
                )
        except Exception as log_e:
            pass

    return success
