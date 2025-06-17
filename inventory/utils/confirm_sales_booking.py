from django.db import transaction
from django.conf import settings
from inventory.models import SalesBooking
from mailer.utils import send_templated_email

def confirm_sales_booking(sales_booking_id, message=None, send_notification=True):
    try:
        with transaction.atomic():
            booking = SalesBooking.objects.select_for_update().get(id=sales_booking_id)
            motorcycle = booking.motorcycle

            if booking.booking_status not in ['confirmed', 'completed']:
                booking.booking_status = 'confirmed'
                booking.save()

                if motorcycle.condition == 'new':
                    if motorcycle.quantity > 0:
                        motorcycle.quantity -= 1
                        if motorcycle.quantity == 0:
                            motorcycle.is_available = False
                            motorcycle.status = 'sold'
                        motorcycle.save()
                else:
                    if motorcycle.is_available:
                        motorcycle.is_available = False
                        motorcycle.status = 'reserved'
                        motorcycle.save()
            else:
                print(f"DEBUG: Booking {sales_booking_id} already confirmed or completed. No action taken.")
                return {'success': False, 'message': 'Booking already confirmed or completed.'}

            if send_notification:
                email_context = {
                    'booking': booking,
                    'sales_profile': booking.sales_profile,
                    'motorcycle': motorcycle,
                    'admin_message': message,
                    'action_type': 'confirmation',
                }

                customer_email_subject = f"Your Sales Booking for {motorcycle.title} is Confirmed!"
                # Corrected template name based on your file tree
                customer_email_template = 'user_sales_booking_approved.html'
                
                print(f"DEBUG: Attempting to send customer confirmation email for booking {booking.sales_booking_reference}")
                print(f"DEBUG: Customer email subject: {customer_email_subject}")
                print(f"DEBUG: Customer email template: {customer_email_template}")
                print(f"DEBUG: Customer recipient: {[booking.sales_profile.email]}")

                send_templated_email(
                    recipient_list=[booking.sales_profile.email],
                    subject=customer_email_subject,
                    template_name=customer_email_template,
                    context=email_context,
                    sales_profile=booking.sales_profile,
                    sales_booking=booking,
                )
                print(f"DEBUG: Customer email for booking {booking.sales_booking_reference} send attempt completed.")


                admin_email_subject = f"ADMIN: Sales Booking {booking.sales_booking_reference} Confirmed"
                # Corrected template name based on your file tree
                admin_email_template = 'admin_sales_booking_approved.html'
                
                print(f"DEBUG: Attempting to send admin confirmation email for booking {booking.sales_booking_reference}")
                print(f"DEBUG: Admin email subject: {admin_email_subject}")
                print(f"DEBUG: Admin email template: {admin_email_template}")
                print(f"DEBUG: Admin recipient: {[settings.DEFAULT_FROM_EMAIL]}")

                send_templated_email(
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    subject=admin_email_subject,
                    template_name=admin_email_template,
                    context=email_context,
                    sales_profile=booking.sales_profile,
                    sales_booking=booking,
                )
                print(f"DEBUG: Admin email for booking {booking.sales_booking_reference} send attempt completed.")

            return {'success': True, 'message': 'Sales booking confirmed successfully.'}

    except SalesBooking.DoesNotExist:
        print(f"DEBUG: Sales Booking with ID {sales_booking_id} not found during confirmation.")
        return {'success': False, 'message': 'Sales Booking not found.'}
    except Exception as e:
        print(f"DEBUG: An error occurred during confirmation for booking {sales_booking_id}: {e}")
        return {'success': False, 'message': f'An error occurred: {str(e)}'}


