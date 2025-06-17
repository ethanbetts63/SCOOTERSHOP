
from django.db import transaction
from django.conf import settings
from inventory.models import SalesBooking
from mailer.utils import send_templated_email

def reject_sales_booking(sales_booking_id, message=None, send_notification=True):
    try:
        with transaction.atomic():
            booking = SalesBooking.objects.select_for_update().get(id=sales_booking_id)
            motorcycle = booking.motorcycle

            new_booking_status = 'declined'
            if booking.payment_status == 'deposit_paid':
                new_booking_status = 'declined_refunded'
            
            if booking.booking_status not in ['cancelled', 'declined', 'declined_refunded']:
                booking.booking_status = new_booking_status
                booking.save()

                if not motorcycle.is_available and motorcycle.status == 'reserved':
                    if motorcycle.condition == 'new':
                        motorcycle.quantity += 1
                        motorcycle.is_available = True
                        motorcycle.status = 'available'
                        motorcycle.save()
                    else:
                        motorcycle.is_available = True
                        motorcycle.status = 'available'
                        motorcycle.save()
            else:
                return {'success': False, 'message': 'Booking already cancelled or declined.'}

            if send_notification:
                email_context = {
                    'booking': booking,
                    'sales_profile': booking.sales_profile,
                    'motorcycle': motorcycle,
                    'admin_message': message,
                    'action_type': 'rejection',
                    'refund_note': True if new_booking_status == 'declined_refunded' else False,
                }

                customer_email_subject = f"Update Regarding Your Sales Booking for {motorcycle.title}"
                customer_email_template = 'emails/sales_booking_rejected_customer.html'
                send_templated_email(
                    recipient_list=[booking.sales_profile.email],
                    subject=customer_email_subject,
                    template_name=customer_email_template,
                    context=email_context,
                    sales_profile=booking.sales_profile,
                    sales_booking=booking,
                )

                admin_email_subject = f"ADMIN: Sales Booking {booking.sales_booking_reference} Rejected"
                admin_email_template = 'emails/sales_booking_rejected_admin.html'
                send_templated_email(
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    subject=admin_email_subject,
                    template_name=admin_email_template,
                    context=email_context,
                    sales_profile=booking.sales_profile,
                    sales_booking=booking,
                )

            return {'success': True, 'message': 'Sales booking rejected successfully.'}

    except SalesBooking.DoesNotExist:
        return {'success': False, 'message': 'Sales Booking not found.'}
    except Exception as e:
        return {'success': False, 'message': f'An error occurred: {str(e)}'}
