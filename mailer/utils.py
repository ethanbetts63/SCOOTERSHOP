# mailer/utils.py

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.db import transaction
import logging
import re
from django.utils import timezone

from .models import EmailLog

try:
    from hire.models import HireBooking
except ImportError:
    HireBooking = None
    logging.warning("Could not import HireBooking model in mailer.utils. Ensure 'hire' app is installed.")

try:
    from hire.models.driver_profile import DriverProfile
except ImportError:
    DriverProfile = None
    logging.warning("Could not import DriverProfile model in mailer.utils. Ensure 'hire' app is installed.")

try:
    from service.models import ServiceProfile, ServiceBooking
except ImportError:
    ServiceProfile = None
    ServiceBooking = None
    logging.warning("Could not import ServiceProfile or ServiceBooking model in mailer.utils. Ensure 'service' app is installed.")


logger = logging.getLogger(__name__)

def send_templated_email(
    recipient_list,
    subject,
    template_name,
    context,
    from_email=None,
    user=None,
    driver_profile=None,
    service_profile=None,
    booking=None
):
    if not recipient_list:
        return False

    sender_email = from_email if from_email else settings.DEFAULT_FROM_EMAIL

    if booking:
        context['booking'] = booking
    if service_profile:
        context['service_profile'] = service_profile

    try:
        html_content = render_to_string(template_name, context)
        text_content_prep = re.sub(r'<br\s*/?>', '\n', html_content)
        text_content_prep = re.sub(r'</p>', '\n\n', text_content_prep)
        text_content_prep = re.sub(r'</(div|h[1-6]|ul|ol|li)>', '\n', text_content_prep)
        text_content_prep = re.sub(r'<(p|div|h[1-6]|ul|ol|li)[^>]*?>', '', text_content_prep)
        text_content = strip_tags(text_content_prep).strip()

    except Exception as e:
        EmailLog.objects.create(
            sender=sender_email,
            recipient=", ".join(recipient_list),
            subject=subject,
            body=f"Error rendering template: {template_name}. Context: {context}",
            status='FAILED',
            error_message=f"Template rendering failed: {e}",
            user=user,
            driver_profile=driver_profile,
            service_profile=service_profile,
            booking=booking if isinstance(booking, HireBooking) else None,
            service_booking=booking if isinstance(booking, ServiceBooking) else None
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
                    timestamp=timezone.now(),
                    sender=sender_email,
                    recipient=", ".join(recipient_list),
                    subject=subject,
                    body=html_content,
                    status=email_status,
                    error_message=error_msg,
                    user=user,
                    driver_profile=driver_profile,
                    service_profile=service_profile,
                    booking=booking if isinstance(booking, HireBooking) else None,
                    service_booking=booking if isinstance(booking, ServiceBooking) else None
                )
        except Exception as log_e:
            pass # Suppress critical logging errors as requested

    return success
