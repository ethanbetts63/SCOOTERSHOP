# mailer/utils.py

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.db import transaction
import logging
from django.utils import timezone
import re # Import regex module

# Import the EmailLog model
from .models import EmailLog

# Import related models for optional linking
# Use try-except for robustness during initial setup or isolated testing
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

# Get the Django logger
logger = logging.getLogger(__name__)

def send_templated_email(
    recipient_list,
    subject,
    template_name,
    context, # This context dictionary is what gets passed to the template
    from_email=None,
    user=None,
    driver_profile=None,
    booking=None # The booking object itself, passed here to be added to context
):
    """
    Sends an HTML email using a Django template and logs the email activity.

    Args:
        recipient_list (list): A list of email addresses to send the email to.
        subject (str): The subject line of the email.
        template_name (str): The path to the HTML template file (e.g., 'emails/booking_confirmation_user.html').
        context (dict): A dictionary of data to pass to the email template for rendering.
                        This dictionary will be updated with 'booking' if provided.
        from_email (str, optional): The sender's email address. Defaults to settings.DEFAULT_FROM_EMAIL.
        user (User, optional): An instance of the User model to link the email log to.
        driver_profile (DriverProfile, optional): An instance of the DriverProfile model to link the email log to.
        booking (HireBooking, optional): An instance of the HireBooking model to link the email log to.

    Returns:
        bool: True if the email was sent successfully, False otherwise.
    """
    if not recipient_list:
        logger.error("send_templated_email called with an empty recipient_list.")
        return False

    # Determine sender email
    sender_email = from_email if from_email else settings.DEFAULT_FROM_EMAIL

    # IMPORTANT: Ensure the booking object is in the context for the template
    # The 'context' parameter is already a dictionary, so we update it.
    if booking:
        context['booking'] = booking

    # Log the full context being passed to the template (for debugging)
    logger.debug(f"Email template context for '{template_name}': {context}")

    # Render HTML content from template
    try:
        html_content = render_to_string(template_name, context)
        
        # NEW FIX: Convert block-level HTML tags to newlines before stripping tags
        # This ensures proper formatting in the plain text version.
        # Replace <br> and </p> with newline characters
        text_content_prep = re.sub(r'<br\s*/?>', '\n', html_content)
        text_content_prep = re.sub(r'</p>', '\n\n', text_content_prep)
        # Replace </div>, <h1>, <h2> etc. with a single newline
        text_content_prep = re.sub(r'</(div|h[1-6]|ul|ol|li)>', '\n', text_content_prep)
        # Replace <p>, <div>, <h1> etc. with their content followed by a newline
        text_content_prep = re.sub(r'<(p|div|h[1-6]|ul|ol|li)[^>]*?>', '', text_content_prep)

        # Finally, strip any remaining HTML tags
        text_content = strip_tags(text_content_prep).strip() # .strip() to remove leading/trailing whitespace

    except Exception as e:
        logger.error(f"Error rendering email template '{template_name}': {e}")
        # Log the failed attempt to render the email
        EmailLog.objects.create(
            sender=sender_email,
            recipient=", ".join(recipient_list),
            subject=subject,
            body=f"Error rendering template: {template_name}. Context: {context}",
            status='FAILED',
            error_message=f"Template rendering failed: {e}",
            user=user,
            driver_profile=driver_profile,
            booking=booking
        )
        return False

    # Initialize status and error message for logging
    email_status = 'PENDING'
    error_msg = None

    try:
        # Create the email message object
        msg = EmailMultiAlternatives(subject, text_content, sender_email, recipient_list)
        msg.attach_alternative(html_content, "text/html")

        # Send the email
        msg.send()
        email_status = 'SENT'
        logger.info(f"Email '{subject}' successfully sent to {', '.join(recipient_list)}")
        success = True
    except Exception as e:
        email_status = 'FAILED'
        error_msg = str(e)
        logger.error(f"Failed to send email '{subject}' to {', '.join(recipient_list)}: {e}")
        success = False
    finally:
        try:
            with transaction.atomic():
                EmailLog.objects.create(
                    timestamp=timezone.now(),
                    sender=sender_email,
                    recipient=", ".join(recipient_list), # Store as comma-separated string
                    subject=subject,
                    body=html_content, # Store HTML body for full record
                    status=email_status,
                    error_message=error_msg,
                    user=user,
                    driver_profile=driver_profile,
                    booking=booking
                )
            logger.debug(f"Email log for '{subject}' to {', '.join(recipient_list)} saved with status: {email_status}")
        except Exception as log_e:
            logger.critical(f"CRITICAL ERROR: Failed to log email for '{subject}' to {', '.join(recipient_list)}: {log_e}")

    return success
