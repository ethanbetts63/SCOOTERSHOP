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
        f"(Ref: {temp_booking.session_uuid})" # Changed from sales_booking_reference to session_uuid
    )

    intent = None
    payment_obj = existing_payment_obj

    if payment_obj and payment_obj.stripe_payment_intent_id:
        # Attempt to retrieve and possibly modify an existing Payment Intent
        try:
            intent = stripe.PaymentIntent.retrieve(payment_obj.stripe_payment_intent_id)

            # Check if intent is not None and its status allows modification/check
            if intent:
                amount_changed = intent.amount != amount_in_cents
                currency_changed = intent.currency.lower() != currency.lower()

                is_modifiable_or_in_progress = intent.status in [
                    'requires_payment_method', 'requires_confirmation', 'requires_action',
                    'processing', 'canceled' # Include 'canceled' if it can be modified from canceled to new status
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
                    # If not modifiable and not succeeded (e.g., already captured/refunded without a new intent needed),
                    # or if the intent is in a terminal state that cannot be reused, create new.
                    # IMPORTANT: 'canceled' can be in this list or 'is_modifiable_or_in_progress' depending on desired Stripe logic.
                    # If a 'canceled' intent can be reactivated/modified, keep it in the modifiable list.
                    # If a 'canceled' intent truly means "start over", then set intent = None here.
                    # For this fix, assume 'canceled' means it can potentially be modified as per common flow
                    # if the amount/currency changes. If not, it falls here to create a new one.
                    intent = None
                
                # Update payment_obj status based on current intent status, even if no modify occurred
                # Only update if intent is not None
                if intent and payment_obj.status != intent.status:
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

