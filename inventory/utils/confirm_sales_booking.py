from django.db import transaction
from django.conf import settings
from inventory.models import SalesBooking
from mailer.utils import send_templated_email

def confirm_sales_booking(sales_booking_id, message=None, send_notification=True):
    try:
        with transaction.atomic():
            booking = SalesBooking.objects.select_for_update().get(id=sales_booking_id)
            motorcycle = booking.motorcycle

            if booking.booking_status not in ["confirmed", "completed"]:
                booking.booking_status = "confirmed"
                booking.save()

                if motorcycle.condition == "new":
                    if motorcycle.quantity > 0:
                        motorcycle.quantity -= 1
                        if motorcycle.quantity == 0:
                            motorcycle.is_available = False
                            motorcycle.status = "sold"
                        motorcycle.save()
                else:
                    if motorcycle.is_available:
                        motorcycle.is_available = False
                        motorcycle.status = "reserved"
                        motorcycle.save()
            else:
                return {
                    "success": False,
                    "message": "Booking already confirmed or completed.",
                }

            if send_notification:
                email_context = {
                    "booking": booking,
                    "sales_profile": booking.sales_profile,
                    "motorcycle": motorcycle,
                    "admin_message": message,
                    "action_type": "confirmation",
                }

                customer_email_subject = (
                    f"Your Sales Booking for {motorcycle.title} is Confirmed!"
                )
                customer_email_template = "user_sales_booking_approved.html"

                send_templated_email(
                    recipient_list=[booking.sales_profile.email],
                    subject=customer_email_subject,
                    template_name=customer_email_template,
                    context=email_context,
                    profile=booking.sales_profile,
                    booking=booking,
                )

                admin_email_subject = (
                    f"ADMIN: Sales Booking {booking.sales_booking_reference} Confirmed"
                )
                admin_email_template = "admin_sales_booking_approved.html"

                send_templated_email(
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    subject=admin_email_subject,
                    template_name=admin_email_template,
                    context=email_context,
                    profile=booking.sales_profile,
                    booking=booking,
                )
            return {"success": True, "message": "Sales booking confirmed successfully."}

    except SalesBooking.DoesNotExist:
        return {"success": False, "message": "Sales Booking not found."}
    except Exception as e:
        return {"success": False, "message": f"An error occurred: {str(e)}"}
