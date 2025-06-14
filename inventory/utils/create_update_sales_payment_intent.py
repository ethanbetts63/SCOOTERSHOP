import stripe
from decimal import Decimal

from payments.models import Payment
from inventory.models import TempSalesBooking, SalesProfile

def create_or_update_sales_payment_intent(
    temp_booking: TempSalesBooking,
    sales_profile: SalesProfile,
    amount_to_pay: Decimal,
    currency: str,
    existing_payment_obj: Payment = None
):
    amount_in_cents = int(amount_to_pay * 100)
    payment_description = (
        f"Deposit for Motorcycle: {temp_booking.motorcycle.year} "
        f"{temp_booking.motorcycle.brand} {temp_booking.motorcycle.model} "
        f"(Ref: {temp_booking.session_uuid})"
    )

    intent = None
    payment_obj = existing_payment_obj

    if payment_obj and payment_obj.stripe_payment_intent_id:
        try:
            intent = stripe.PaymentIntent.retrieve(payment_obj.stripe_payment_intent_id)

            if intent:
                amount_changed = intent.amount != amount_in_cents
                currency_changed = intent.currency.lower() != currency.lower()

                # Removed 'canceled' from this list, so it falls into the 'intent = None' case below
                is_modifiable_or_in_progress = intent.status in [
                    'requires_payment_method', 'requires_confirmation', 'requires_action',
                    'processing'
                ]

                if (amount_changed or currency_changed) and is_modifiable_or_in_progress:
                    intent = stripe.PaymentIntent.modify(
                        payment_obj.stripe_payment_intent_id,
                        amount=amount_in_cents,
                        currency=currency,
                        description=payment_description,
                        metadata={
                            'temp_sales_booking_uuid': str(temp_booking.session_uuid),
                            'sales_profile_id': str(sales_profile.id) if sales_profile else 'guest',
                            'booking_type': 'sales_booking',
                        }
                    )
                elif intent.status == 'failed' or intent.status == 'canceled': # Explicitly handle 'canceled' here
                    intent = None
                elif not is_modifiable_or_in_progress and intent.status != 'succeeded':
                    intent = None
                
                if intent and payment_obj.status != intent.status:
                    payment_obj.status = intent.status
                    payment_obj.save()

        except stripe.error.StripeError:
            intent = None

    if not intent:
        intent = stripe.PaymentIntent.create(
            amount=amount_in_cents,
            currency=currency,
            metadata={
                'temp_sales_booking_uuid': str(temp_booking.session_uuid),
                'sales_profile_id': str(sales_profile.id) if sales_profile else 'guest',
                'booking_type': 'sales_booking',
            },
            description=payment_description
        )

    if payment_obj:
        payment_obj.stripe_payment_intent_id = intent.id
        payment_obj.amount = amount_to_pay
        payment_obj.currency = currency
        payment_obj.status = intent.status
        payment_obj.description = payment_description
        if sales_profile and not payment_obj.sales_customer_profile:
            payment_obj.sales_customer_profile = sales_profile
        payment_obj.save()
    else:
        payment_obj = Payment.objects.create(
            temp_sales_booking=temp_booking,
            sales_customer_profile=sales_profile,
            stripe_payment_intent_id=intent.id,
            amount=amount_to_pay,
            currency=currency,
            status=intent.status,
            description=payment_description
        )
    
    return intent, payment_obj

