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
    """
    Creates or updates a Stripe Payment Intent and the associated Payment Django object
    for a sales booking.

    Args:
        temp_booking (TempSalesBooking): The temporary sales booking instance.
        sales_profile (SalesProfile): The sales profile associated with the booking.
        amount_to_pay (Decimal): The amount to charge for the payment intent.
        currency (str): The currency code (e.g., 'AUD').
        existing_payment_obj (Payment, optional): An existing Payment object to update.
                                                  If None, a new one will be created.

    Returns:
        tuple: A tuple containing (stripe.PaymentIntent, Payment) on success.

    Raises:
        stripe.error.StripeError: If any Stripe API error occurs.
        Exception: For other unexpected errors.
    """
    amount_in_cents = int(amount_to_pay * 100)
    payment_description = (
        f"Deposit for Motorcycle: {temp_booking.motorcycle.year} "
        f"{temp_booking.motorcycle.brand} {temp_booking.motorcycle.model} "
        f"(Ref: {temp_booking.sales_booking_reference})"
    )

    intent = None
    payment_obj = existing_payment_obj

    if payment_obj and payment_obj.stripe_payment_intent_id:
        # Attempt to retrieve and possibly modify an existing Payment Intent
        try:
            intent = stripe.PaymentIntent.retrieve(payment_obj.stripe_payment_intent_id)

            amount_changed = intent.amount != amount_in_cents
            currency_changed = intent.currency.lower() != currency.lower()
            
            is_modifiable_or_in_progress = intent.status in [
                'requires_payment_method', 'requires_confirmation', 'requires_action',
                'processing', 'canceled'
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
            elif intent.status == 'failed':
                intent = None # Treat failed intents as needing a new one
            elif not is_modifiable_or_in_progress and intent.status != 'succeeded':
                intent = None # If not modifiable and not succeeded, create new
            
            # Update payment_obj status based on current intent status, even if no modify
            if payment_obj.status != intent.status:
                payment_obj.status = intent.status
                payment_obj.save()

        except stripe.error.StripeError:
            # If retrieval fails (e.g., PI not found), proceed to create a new one
            intent = None

    if not intent:
        # Create a new Payment Intent if no existing valid one or retrieval failed
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

    # Create or update the Django Payment object
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

