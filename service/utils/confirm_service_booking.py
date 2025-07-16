from django.db import transaction
from django.conf import settings
from service.models import ServiceBooking
from mailer.utils import send_templated_email
from dashboard.models import SiteSettings

def confirm_service_booking(service_booking_id, message=None, send_notification=True):
    try:
        with transaction.atomic():
            booking = ServiceBooking.objects.select_for_update().get(id=service_booking_id)

            if booking.booking_status not in ["confirmed", "completed", "in_progress"]:
                booking.booking_status = "confirmed"
                booking.save()
            else:
                return {
                    "success": False,
                    "message": "Booking already confirmed, in progress, or completed.",
                }

            if send_notification:
                site_settings = SiteSettings.get_settings()
                email_context = {
                    "booking": booking,
                    "service_profile": booking.service_profile,
                    "customer_motorcycle": booking.customer_motorcycle,
                    "admin_message": message,
                    "action_type": "confirmation",
                    "SITE_DOMAIN": settings.SITE_DOMAIN,
                    "SITE_SCHEME": settings.SITE_SCHEME,
                    "site_settings": site_settings,
                }

                customer_email_subject = (
                    f"Your Service Booking {booking.service_booking_reference} is Confirmed!"
                )
                customer_email_template = "user_service_booking_approved.html"

                send_templated_email(
                    recipient_list=[booking.service_profile.email],
                    subject=customer_email_subject,
                    template_name=customer_email_template,
                    context=email_context,
                    profile=booking.service_profile,
                    booking=booking,
                )

                admin_email_subject = (
                    f"ADMIN: Service Booking {booking.service_booking_reference} Confirmed"
                )
                admin_email_template = "admin_service_booking_approved.html"

                send_templated_email(
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    subject=admin_email_subject,
                    template_name=admin_email_template,
                    context=email_context,
                    profile=booking.service_profile,
                    booking=booking,
                )
            return {"success": True, "message": "Service booking confirmed successfully."}

    except ServiceBooking.DoesNotExist:
        return {"success": False, "message": "Service Booking not found."}
    except Exception as e:
        return {"success": False, "message": f"An error occurred: {str(e)}"}
