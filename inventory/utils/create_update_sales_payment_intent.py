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

    stripe_intent = None
    django_payment_obj = None

    if existing_payment_obj and existing_payment_obj.stripe_payment_intent_id:
        try:
            retrieved_intent = stripe.PaymentIntent.retrieve(existing_payment_obj.stripe_payment_intent_id)

            if retrieved_intent:
                amount_changed = retrieved_intent.amount != amount_in_cents
                currency_changed = retrieved_intent.currency.lower() != currency.lower()

                is_modifiable_or_in_progress = retrieved_intent.status in [
                    'requires_payment_method', 'requires_confirmation', 'requires_action',
                    'processing'
                ]

                if (amount_changed or currency_changed) and is_modifiable_or_in_progress:
                    stripe_intent = stripe.PaymentIntent.modify(
                        existing_payment_obj.stripe_payment_intent_id,
                        amount=amount_in_cents,
                        currency=currency,
                        description=payment_description,
                        metadata={
                            'temp_sales_booking_uuid': str(temp_booking.session_uuid),
                            'sales_profile_id': str(sales_profile.id) if sales_profile else 'guest',
                            'booking_type': 'sales_booking',
                        }
                    )
                    django_payment_obj = existing_payment_obj

                elif retrieved_intent.status in ['failed', 'canceled']:
                    stripe_intent = None
                    django_payment_obj = None

                elif not is_modifiable_or_in_progress and retrieved_intent.status != 'succeeded':
                    stripe_intent = None
                    django_payment_obj = None
                
                else:
                    stripe_intent = retrieved_intent
                    django_payment_obj = existing_payment_obj

                if django_payment_obj and stripe_intent and django_payment_obj.status != stripe_intent.status:
                    django_payment_obj.status = stripe_intent.status
                    django_payment_obj.save()

        except stripe.error.StripeError as e:
            stripe_intent = None
            django_payment_obj = None

    if not stripe_intent:
        stripe_intent = stripe.PaymentIntent.create(
            amount=amount_in_cents,
            currency=currency,
            metadata={
                'temp_sales_booking_uuid': str(temp_booking.session_uuid),
                'sales_profile_id': str(sales_profile.id) if sales_profile else 'guest',
                'booking_type': 'sales_booking',
            },
            description=payment_description
        )
        django_payment_obj = Payment.objects.create(
            temp_sales_booking=temp_booking,
            sales_customer_profile=sales_profile,
            stripe_payment_intent_id=stripe_intent.id,
            amount=amount_to_pay,
            currency=currency,
            status=stripe_intent.status,
            description=payment_description
        )
    elif django_payment_obj and django_payment_obj.stripe_payment_intent_id != stripe_intent.id:
        pass

    if django_payment_obj:
        django_payment_obj.amount = amount_to_pay
        django_payment_obj.currency = currency
        django_payment_obj.description = payment_description
        if sales_profile and not django_payment_obj.sales_customer_profile:
            django_payment_obj.sales_customer_profile = sales_profile
        django_payment_obj.save()

    return stripe_intent, django_payment_obj

