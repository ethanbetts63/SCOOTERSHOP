from django.db import transaction
from decimal import Decimal
import uuid

from service.models import TempServiceBooking, ServiceBooking, ServiceSettings
from payments.models import Payment, RefundPolicySettings # Ensure RefundPolicySettings is imported

def convert_temp_service_booking(
    temp_booking,
    payment_method,
    booking_payment_status,
    amount_paid_on_booking,
    calculated_total_on_booking,
    stripe_payment_intent_id = None,
    payment_obj = None, # This can be an existing Payment instance or None
):
    print(f"\n--- convert_temp_service_booking START ---")
    print(f"temp_booking ID: {temp_booking.pk}")
    print(f"Initial payment_obj: {payment_obj.pk if payment_obj else 'None'}")
    print(f"amount_paid_on_booking: {amount_paid_on_booking}")
    print(f"calculated_total_on_booking: {calculated_total_on_booking}")
    
    try:
        with transaction.atomic():
            service_settings = ServiceSettings.objects.first()

            currency_code = 'AUD' # Default currency if service_settings is not found
            if service_settings:
                currency_code = service_settings.currency_code
            print(f"Currency Code: {currency_code}")
                
            service_booking_reference = f"SVC-{uuid.uuid4().hex[:8].upper()}"

            # --- Create ServiceBooking ---
            print(f"Creating ServiceBooking...")
            service_booking = ServiceBooking.objects.create(
                service_booking_reference=service_booking_reference,
                service_type=temp_booking.service_type,
                service_profile=temp_booking.service_profile,
                customer_motorcycle=temp_booking.customer_motorcycle,
                payment_option=temp_booking.payment_option,
                calculated_total=calculated_total_on_booking,
                calculated_deposit_amount=temp_booking.calculated_deposit_amount if temp_booking.calculated_deposit_amount is not None else Decimal('0.00'),
                amount_paid=amount_paid_on_booking, # Amount paid on booking
                payment_status=booking_payment_status,
                payment_method=payment_method,
                currency=currency_code,
                stripe_payment_intent_id=stripe_payment_intent_id,
                service_date=temp_booking.service_date,
                dropoff_date=temp_booking.dropoff_date,
                dropoff_time=temp_booking.dropoff_time,
                estimated_pickup_date=temp_booking.estimated_pickup_date,
                booking_status='confirmed',
                customer_notes=temp_booking.customer_notes,
                payment=payment_obj, # Link the payment object to the service booking (can be None)
            )
            print(f"ServiceBooking created: {service_booking.pk}")

            # --- Handle Payment Object Updates (ONLY if payment_obj exists) ---
            if payment_obj:
                print(f"Payment object provided. Updating payment_obj (PK: {payment_obj.pk})...")
                print(f"payment_obj.amount BEFORE update: {payment_obj.amount}")
                payment_obj.amount = amount_paid_on_booking # Ensure amount is updated if an object is passed
                print(f"payment_obj.amount AFTER update: {payment_obj.amount}")
                
                payment_obj.currency = currency_code
                payment_obj.status = booking_payment_status
                payment_obj.stripe_payment_intent_id = stripe_payment_intent_id
                payment_obj.service_booking = service_booking
                payment_obj.service_customer_profile = service_booking.service_profile
                
                # Detach temp_service_booking from payment_obj as it's now converted
                if hasattr(payment_obj, 'temp_service_booking') and payment_obj.temp_service_booking:
                    print(f"Detaching temp_service_booking from payment_obj.")
                    payment_obj.temp_service_booking = None

                # --- Populate Refund Policy Snapshot ---
                print(f"Attempting to populate refund_policy_snapshot...")
                try:
                    refund_settings = RefundPolicySettings.objects.first()
                    if refund_settings:
                        print(f"RefundPolicySettings found. Creating snapshot.")
                        # Create a snapshot, converting Decimal fields to float for JSON serialization.
                        payment_obj.refund_policy_snapshot = {
                            'cancellation_full_payment_full_refund_days': refund_settings.cancellation_full_payment_full_refund_days,
                            'cancellation_full_payment_partial_refund_days': refund_settings.cancellation_full_payment_partial_refund_days,
                            'cancellation_full_payment_partial_refund_percentage': float(refund_settings.cancellation_full_payment_partial_refund_percentage),
                            'cancellation_full_payment_minimal_refund_days': refund_settings.cancellation_full_payment_minimal_refund_days,
                            'cancellation_full_payment_minimal_refund_percentage': float(refund_settings.cancellation_full_payment_minimal_refund_percentage),
                            
                            'cancellation_deposit_full_refund_days': refund_settings.cancellation_deposit_full_refund_days,
                            'cancellation_deposit_partial_refund_days': refund_settings.cancellation_deposit_partial_refund_days,
                            'cancellation_deposit_partial_refund_percentage': float(refund_settings.cancellation_deposit_partial_refund_percentage),
                            'cancellation_deposit_minimal_refund_days': refund_settings.cancellation_deposit_minimal_refund_days,
                            'cancellation_deposit_minimal_refund_percentage': float(refund_settings.cancellation_deposit_minimal_refund_percentage),

                            'refund_deducts_stripe_fee_policy': refund_settings.refund_deducts_stripe_fee_policy,
                            'stripe_fee_percentage_domestic': float(refund_settings.stripe_fee_percentage_domestic),
                            'stripe_fee_fixed_domestic': float(refund_settings.stripe_fee_fixed_domestic),
                            'stripe_fee_percentage_international': float(refund_settings.stripe_fee_percentage_international),
                            'stripe_fee_fixed_international': float(refund_settings.stripe_fee_fixed_international),
                        }
                    else:
                        print(f"No RefundPolicySettings found. Snapshot will be empty.")
                        # If no RefundPolicySettings exist, ensure the snapshot is an empty dict
                        payment_obj.refund_policy_snapshot = {}
                except Exception as e:
                    print(f"Error creating refund policy snapshot: {e}")
                    payment_obj.refund_policy_snapshot = {} # Ensure it's still an empty dict on error

                print(f"Calling payment_obj.save()...")
                payment_obj.save() # Save the payment object with all updates and snapshot
                print(f"payment_obj saved. Current amount: {payment_obj.amount}")
            else:
                print(f"No payment_obj provided. Skipping payment object updates.")


            print(f"Deleting temp_booking (PK: {temp_booking.pk})...")
            temp_booking.delete()
            print(f"temp_booking deleted.")

            print(f"--- convert_temp_service_booking END ---")
            return service_booking

    except Exception as e:
        print(f"--- convert_temp_service_booking ERROR: {e} ---")
        raise # Re-raise the exception after logging if needed
