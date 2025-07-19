from django.db import transaction
from django.conf import settings
from service.models import ServiceBooking
from mailer.utils import send_templated_email
from refunds.utils.create_refund_request import create_refund_request
from dashboard.models import SiteSettings


def reject_service_booking(
    service_booking_id, requesting_user=None, form_data=None, send_notification=True
):
    if form_data is None:
        form_data = {}
    message = form_data.get("message")

    try:
        with transaction.atomic():
            booking = ServiceBooking.objects.select_for_update().get(
                id=service_booking_id
            )

            original_booking_status = booking.booking_status

            refund_request_created = False
            refund_amount_initiated = None
            refund_request_pk = None

            initiate_refund_checkbox = form_data.get("initiate_refund", False)

            if original_booking_status not in [
                "cancelled",
                "declined",
                "DECLINED_REFUNDED",
            ]:
                if (
                    booking.payment_status == "deposit_paid"
                    and initiate_refund_checkbox
                ):
                    refund_amount_value = form_data.get("refund_amount")
                    if refund_amount_value is None:
                        return {
                            "success": False,
                            "message": "Refund amount is required to initiate a refund.",
                        }

                    created_refund_req = create_refund_request(
                        amount_to_refund=refund_amount_value,
                        reason=f"Service Booking {booking.service_booking_reference} rejected by admin."
                        + (f" Admin message: {message}" if message else ""),
                        payment=booking.payment,
                        service_booking=booking,
                        requesting_user=requesting_user,
                        service_profile=booking.service_profile,
                        is_admin_initiated=True,
                        staff_notes=f"Admin rejected booking and initiated refund request for {booking.service_booking_reference}. Amount: {refund_amount_value}"
                        + (f" Admin message: {message}" if message else ""),
                        initial_status="reviewed_pending_approval",
                    )

                    if created_refund_req:
                        refund_request_created = True
                        refund_amount_initiated = refund_amount_value
                        refund_request_pk = created_refund_req.pk
                        booking.booking_status = "declined"
                    else:
                        return {
                            "success": False,
                            "message": "Failed to create refund request for rejected booking.",
                        }
                else:
                    if booking.payment_status == "deposit_paid":
                        booking.booking_status = "DECLINED_REFUNDED"
                    else:
                        booking.booking_status = "declined"

                booking.save()

            else:
                return {
                    "success": False,
                    "message": "Booking already cancelled or declined.",
                }

            if send_notification and not refund_request_created:
                site_settings = SiteSettings.get_settings()
                email_context = {
                    "booking": booking,
                    "service_profile": booking.service_profile,
                    "customer_motorcycle": booking.customer_motorcycle,
                    "admin_message": message,
                    "action_type": "rejection",
                    "refund_request_pending": (
                        False if not refund_request_created else True
                    ),
                    "refund_amount_requested": refund_amount_initiated,
                    "SITE_DOMAIN": settings.SITE_DOMAIN,
                    "SITE_SCHEME": settings.SITE_SCHEME,
                    "site_settings": site_settings,
                }

                customer_email_subject = f"Update Regarding Your Service Booking {booking.service_booking_reference}"
                customer_email_template = "user_service_booking_rejected.html"
                send_templated_email(
                    recipient_list=[booking.service_profile.email],
                    subject=customer_email_subject,
                    template_name=customer_email_template,
                    context=email_context,
                    profile=booking.service_profile,
                    booking=booking,
                )

                admin_email_subject = f"ADMIN: Service Booking {booking.service_booking_reference} Rejected"
                admin_email_template = "admin_service_booking_rejected.html"
                send_templated_email(
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    subject=admin_email_subject,
                    template_name=admin_email_template,
                    context=email_context,
                    profile=booking.service_profile,
                    booking=booking,
                )

            success_message = "Service booking rejected successfully."
            if refund_request_created:
                success_message += f" A refund request for {refund_amount_initiated} has been created and will be processed automatically."

            return_data = {"success": True, "message": success_message}
            if refund_request_created:
                return_data["refund_request_pk"] = refund_request_pk
            return return_data

    except ServiceBooking.DoesNotExist:
        return {"success": False, "message": "Service Booking not found."}
    except Exception as e:
        return {"success": False, "message": f"An error occurred: {str(e)}"}
