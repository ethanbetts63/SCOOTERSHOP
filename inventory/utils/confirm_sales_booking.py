from django.db import transaction
from django.conf import settings
from inventory.models import SalesBooking
from mailer.utils import send_templated_email


def confirm_sales_booking(sales_booking_id, message=None, send_notification=True):
    print("--- 1. ENTERING confirm_sales_booking function ---")
    try:
        with transaction.atomic():
            booking = SalesBooking.objects.select_for_update().get(id=sales_booking_id)
            motorcycle = booking.motorcycle
            print("--- 2. SUCCESSFULLY FETCHED booking and motorcycle ---")

            if booking.booking_status not in ["confirmed", "completed"]:
                booking.booking_status = "confirmed"
                booking.save()
                print("--- 3. BOOKING status updated and saved ---")

                if motorcycle.condition == "new":
                    if motorcycle.quantity > 0:
                        motorcycle.quantity -= 1
                        if motorcycle.quantity == 0:
                            motorcycle.is_available = False
                            motorcycle.status = "sold"
                        motorcycle.save()
                        print("--- 4a. NEW motorcycle quantity updated and saved ---")
                else:
                    if motorcycle.is_available:
                        motorcycle.is_available = False
                        motorcycle.status = "reserved"
                        motorcycle.save()
                        print("--- 4b. USED motorcycle status updated and saved ---")
            else:
                print("--- X. FAILED: Booking already confirmed or completed ---")
                return {
                    "success": False,
                    "message": "Booking already confirmed or completed.",
                }

            if send_notification:
                print("--- 5. PREPARING to send notifications ---")
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

                print("--- 6. ATTEMPTING to send CUSTOMER email ---")
                send_templated_email(
                    recipient_list=[booking.sales_profile.email],
                    subject=customer_email_subject,
                    template_name=customer_email_template,
                    context=email_context,
                    sales_profile=booking.sales_profile,
                    sales_booking=booking,
                )
                print("--- 7. SUCCESSFULLY sent CUSTOMER email ---")

                admin_email_subject = (
                    f"ADMIN: Sales Booking {booking.sales_booking_reference} Confirmed"
                )
                admin_email_template = "admin_sales_booking_approved.html"

                print("--- 8. ATTEMPTING to send ADMIN email ---")
                send_templated_email(
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    subject=admin_email_subject,
                    template_name=admin_email_template,
                    context=email_context,
                    sales_profile=booking.sales_profile,
                    sales_booking=booking,
                )
                print("--- 9. SUCCESSFULLY sent ADMIN email ---")

            print("--- 10. RETURNING SUCCESS ---")
            return {"success": True, "message": "Sales booking confirmed successfully."}

    except SalesBooking.DoesNotExist:
        print("--- X. FAILED: SalesBooking.DoesNotExist ---")
        return {"success": False, "message": "Sales Booking not found."}
    except Exception as e:
        # This will catch the hidden error and print it to the console
        print(f"--- X. FAILED with a general exception: {e} ---")
        return {"success": False, "message": f"An error occurred: {str(e)}"}
