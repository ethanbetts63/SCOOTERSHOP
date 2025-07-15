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
    print(f"[send_templated_email] Recipient list: {recipient_list}")
    print(f"[send_templated_email] Subject: {subject}")
    print(f"[send_templated_email] Template name: {template_name}")

    if not recipient_list:
        print("[send_templated_email] Recipient list is empty. Returning False.")
        return False

    sender_email = from_email if from_email else settings.DEFAULT_FROM_EMAIL
    print(f"[send_templated_email] Sender email: {sender_email}")

    user = getattr(profile, 'user', None)

    service_profile = profile if isinstance(profile, ServiceProfile) else None
    sales_profile = profile if isinstance(profile, SalesProfile) else None
    service_booking_obj = booking if isinstance(booking, ServiceBooking) else None
    sales_booking_obj = booking if isinstance(booking, SalesBooking) else None

    context['booking'] = booking
    context['profile'] = profile
    context['user'] = user

    html_content = None
    text_content = None
    try:
        html_content = render_to_string(template_name, context)
        text_content_prep = re.sub(r'<br\s*?>', '\n', html_content)
        text_content_prep = re.sub(r'</p>', '\n\n', text_content_prep)
        text_content_prep = re.sub(r'</(div|h[1-6]|ul|ol|li)>', '\n', text_content_prep)
        text_content_prep = re.sub(r'<(p|div|h[1-6]|ul|ol|li)[^>]*?>', '', text_content_prep)
        text_content = strip_tags(text_content_prep).strip()
        print("[send_templated_email] Template rendered successfully.")

    except Exception as e:
        error_msg = f"Template rendering failed: {e}"
        print(f"[send_templated_email] {error_msg}")
        EmailLog.objects.create(
            sender=sender_email, recipient=", ".join(recipient_list), subject=subject,
            status='FAILED',
            error_message=error_msg, user=user,
            service_profile=service_profile,
            sales_profile=sales_profile,
            service_booking=service_booking_obj, sales_booking=sales_booking_obj,
        )
        return False # Return False immediately on template rendering failure

    email_status = 'PENDING'
    error_msg = None
    success = False

    try:
        msg = EmailMultiAlternatives(subject, text_content, sender_email, recipient_list)
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        email_status = 'SENT'
        success = True
        print("[send_templated_email] Email sent successfully via msg.send().")
    except Exception as e:
        email_status = 'FAILED'
        error_msg = str(e)
        success = False
        print(f"[send_templated_email] Error during msg.send(): {error_msg}")

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

    if not success and error_msg:
        print(f"[send_templated_email] Final email sending status: FAILED. Error: {error_msg}")
    elif not success:
        print("[send_templated_email] Final email sending status: FAILED (no specific error message captured).")
    else:
        print("[send_templated_email] Final email sending status: SUCCESS.")

    return success