from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.db import transaction
import re
from django.utils import timezone
from mailer.models.EmailLog_model import EmailLog
from service.models import ServiceBooking, ServiceProfile
from inventory.models import SalesBooking, SalesProfile

def send_templated_email(
    recipient_list,
    subject,
    template_name,
    context,
    booking,
    profile,
    from_email=None,
):
    if not recipient_list:
        return False

    sender_email = from_email if from_email else settings.DEFAULT_FROM_EMAIL

    user = getattr(profile, 'user', None)

    service_profile = profile if isinstance(profile, ServiceProfile) else None
    sales_profile = profile if isinstance(profile, SalesProfile) else None
    service_booking_obj = booking if isinstance(booking, ServiceBooking) else None
    sales_booking_obj = booking if isinstance(booking, SalesBooking) else None
    
    context['booking'] = booking
    context['profile'] = profile
    context['user'] = user
                              
    try:
        html_content = render_to_string(template_name, context)
        text_content_prep = re.sub(r'<br\s*?>', '\n', html_content)
        text_content_prep = re.sub(r'</p>', '\n\n', text_content_prep)
        text_content_prep = re.sub(r'</(div|h[1-6]|ul|ol|li)>', '\n', text_content_prep)
        text_content_prep = re.sub(r'<(p|div|h[1-6]|ul|ol|li)[^>]*?>', '', text_content_prep)
        text_content = strip_tags(text_content_prep).strip()

    except Exception as e:
        # We still log template rendering failures as this happens before the admin check.
        EmailLog.objects.create(
            sender=sender_email, recipient=", ".join(recipient_list), subject=subject,
            status='FAILED',
            error_message=f"Template rendering failed: {e}", user=user,
            service_profile=service_profile,
            sales_profile=sales_profile,
            service_booking=service_booking_obj, sales_booking=sales_booking_obj,
        )
        return False

    email_status = 'PENDING'
    error_msg = None
    success = False

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
        print(f"[send_templated_email] Error sending email: {error_msg}")

    if settings.ADMIN_EMAIL not in recipient_list:
        try:
            with transaction.atomic():
                log_entry = EmailLog(
                    timestamp=timezone.now(),
                    sender=sender_email,
                    recipient=", ".join(recipient_list),
                    subject=subject,
                    html_content=html_content,
                    status=email_status,
                    error_message=error_msg,
                    user=user,
                    service_profile=service_profile,
                    sales_profile=sales_profile,
                    service_booking=service_booking_obj,
                    sales_booking=sales_booking_obj,
                )
                log_entry.save()
        except Exception as log_e:
            print(f"Failed to create email log: {log_e}")

    return success
