# mailer/utils.py

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.db import transaction
import logging
import re
from django.utils import timezone

# Import the EmailLog model
from .models import EmailLog

# Import related models for optional linking
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
    from service.models import ServiceProfile
except ImportError:
    ServiceProfile = None
    logging.warning("Could not import ServiceProfile model in mailer.utils. Ensure 'service' app is installed.")


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
    print(f"DEBUG EMAIL: send_templated_email called for subject: '{subject}' to recipients: {recipient_list}")

    if not recipient_list:
        print("DEBUG EMAIL: Recipient list is empty. Aborting email send.")
        return False

    sender_email = from_email if from_email else settings.DEFAULT_FROM_EMAIL
    print(f"DEBUG EMAIL: Sender email: {sender_email}")

    if booking:
        context['booking'] = booking
    if service_profile:
        context['service_profile'] = service_profile

    # Debug: Print the full context before rendering
    print(f"DEBUG EMAIL: Context for template '{template_name}': {context}")

    try:
        html_content = render_to_string(template_name, context)
        print(f"DEBUG EMAIL: HTML content rendered from template '{template_name}'. Length: {len(html_content)} characters.")

        text_content_prep = re.sub(r'<br\s*/?>', '\n', html_content)
        text_content_prep = re.sub(r'</p>', '\n\n', text_content_prep)
        text_content_prep = re.sub(r'</(div|h[1-6]|ul|ol|li)>', '\n', text_content_prep)
        text_content_prep = re.sub(r'<(p|div|h[1-6]|ul|ol|li)[^>]*?>', '', text_content_prep)
        text_content = strip_tags(text_content_prep).strip()
        print(f"DEBUG EMAIL: Plain text content generated. Length: {len(text_content)} characters.")

    except Exception as e:
        print(f"ERROR EMAIL: Error rendering email template '{template_name}': {e}")
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
            booking=booking
        )
        print("DEBUG EMAIL: Email log created with FAILED status due to template rendering error.")
        return False

    email_status = 'PENDING'
    error_msg = None

    try:
        msg = EmailMultiAlternatives(subject, text_content, sender_email, recipient_list)
        msg.attach_alternative(html_content, "text/html")
        print(f"DEBUG EMAIL: EmailMultiAlternatives object created. Attempting to send...")
        msg.send()
        email_status = 'SENT'
        print(f"DEBUG EMAIL: Email '{subject}' successfully sent to {', '.join(recipient_list)}")
        success = True
    except Exception as e:
        email_status = 'FAILED'
        error_msg = str(e)
        print(f"ERROR EMAIL: Failed to send email '{subject}' to {', '.join(recipient_list)}: {e}")
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
                    booking=booking
                )
            print(f"DEBUG EMAIL: Email log for '{subject}' to {', '.join(recipient_list)} saved with status: {email_status}")
        except Exception as log_e:
            print(f"CRITICAL ERROR EMAIL: Failed to log email for '{subject}' to {', '.join(recipient_list)}: {log_e}")

    return success
