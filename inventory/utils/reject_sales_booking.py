from django.db import transaction
from django.conf import settings
from inventory.models import SalesBooking
from mailer.utils import send_templated_email
from payments.utils.create_refund_request import create_refund_request
from payments.models import Payment

def reject_sales_booking(sales_booking_id, requesting_user=None, form_data=None, send_notification=True):
    if form_data is None:
        form_data = {}
    message = form_data.get('message')

    try:
        with transaction.atomic():
            booking = SalesBooking.objects.select_for_update().get(id=sales_booking_id)
            motorcycle = booking.motorcycle

            original_booking_status = booking.booking_status
            
            refund_request_created = False
            refund_amount_initiated = None
            refund_request_pk = None                     
            
            initiate_refund_checkbox = form_data.get('initiate_refund', False)
            
            if original_booking_status not in ['cancelled', 'declined', 'declined_refunded']:
                if booking.payment_status == 'deposit_paid' and initiate_refund_checkbox:
                    refund_amount_value = form_data.get('refund_amount')
                    if refund_amount_value is None:
                         return {'success': False, 'message': 'Refund amount is required to initiate a refund.'}
                    
                    created_refund_req = create_refund_request(
                        amount_to_refund=refund_amount_value,
                        reason=f"Sales Booking {booking.sales_booking_reference} rejected by admin." + (f" Admin message: {message}" if message else ""),
                        payment=booking.payment,
                        sales_booking=booking,
                        requesting_user=requesting_user,
                        sales_profile=booking.sales_profile,
                        is_admin_initiated=True,
                        staff_notes=f"Admin rejected booking and initiated refund request for {booking.sales_booking_reference}. Amount: {refund_amount_value}" + (f" Admin message: {message}" if message else ""),
                        initial_status='approved',                                                                
                    )

                    if created_refund_req:
                        refund_request_created = True
                        refund_amount_initiated = refund_amount_value
                        refund_request_pk = created_refund_req.pk               
                        booking.booking_status = 'declined' 
                    else:
                        return {'success': False, 'message': 'Failed to create refund request for rejected booking.'}
                else:
                    if booking.payment_status == 'deposit_paid':
                        booking.booking_status = 'declined_refunded' 
                    else:
                        booking.booking_status = 'declined'
                
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

            if send_notification and not refund_request_created:
                email_context = {
                    'booking': booking,
                    'sales_profile': booking.sales_profile,
                    'motorcycle': motorcycle,
                    'admin_message': message,
                    'action_type': 'rejection',
                    'refund_request_pending': False,
                    'refund_amount_requested': None,
                }

                customer_email_subject = f"Update Regarding Your Sales Booking for {motorcycle.title}"
                customer_email_template = 'user_sales_booking_rejected.html'
                send_templated_email(
                    recipient_list=[booking.sales_profile.email],
                    subject=customer_email_subject,
                    template_name=customer_email_template,
                    context=email_context,
                    sales_profile=booking.sales_profile,
                    sales_booking=booking,
                )

                admin_email_subject = f"ADMIN: Sales Booking {booking.sales_booking_reference} Rejected"
                admin_email_template = 'admin_sales_booking_rejected.html'
                send_templated_email(
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    subject=admin_email_subject,
                    template_name=admin_email_template,
                    context=email_context,
                    sales_profile=booking.sales_profile,
                    sales_booking=booking,
                )
            
            success_message = f"Sales booking rejected successfully."
            if refund_request_created:
                success_message += f" A refund request for {refund_amount_initiated} has been created and will be processed automatically."
                
                                                                                        
            return_data = {'success': True, 'message': success_message}
            if refund_request_created:
                return_data['refund_request_pk'] = refund_request_pk
            return return_data

    except SalesBooking.DoesNotExist:
        return {'success': False, 'message': 'Sales Booking not found.'}
    except Exception as e:
        return {'success': False, 'message': f'An error occurred: {str(e)}'}
