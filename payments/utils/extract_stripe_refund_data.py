from django.conf import settings
from decimal import Decimal
import stripe


def extract_stripe_refund_data(event_object_data: dict) -> dict:
    is_charge_object = event_object_data.get("object") == "charge"
    is_refund_object = event_object_data.get("object") == "refund"

    refunded_amount_decimal = Decimal("0.00")
    stripe_refund_id = None
    refund_status = None
    charge_id = None

    if is_charge_object:
        refunded_amount_cents = event_object_data.get("amount_refunded")
        if refunded_amount_cents is not None:
            refunded_amount_decimal = Decimal(refunded_amount_cents) / Decimal("100")

        if (
            "refunds" in event_object_data
            and event_object_data["refunds"]
            and "data" in event_object_data["refunds"]
            and event_object_data["refunds"]["data"]
        ):
            latest_refund = max(
                event_object_data["refunds"]["data"], key=lambda r: r["created"]
            )
            stripe_refund_id = latest_refund.get("id")
            refund_status = latest_refund.get("status")
        charge_id = event_object_data.get("id")

    elif is_refund_object:
        stripe_refund_id = event_object_data.get("id")
        refund_status = event_object_data.get("status")
        charge_id = event_object_data.get("charge")

        if charge_id:
            try:
                stripe.api_key = settings.STRIPE_SECRET_KEY
                latest_charge = stripe.Charge.retrieve(charge_id)
                if latest_charge and latest_charge.get("amount_refunded") is not None:
                    refunded_amount_decimal = Decimal(
                        latest_charge.get("amount_refunded")
                    ) / Decimal("100")
                else:
                    if event_object_data.get("amount") is not None:
                        refunded_amount_decimal = Decimal(
                            event_object_data.get("amount")
                        ) / Decimal("100")
            except stripe.error.StripeError:
                if event_object_data.get("amount") is not None:
                    refunded_amount_decimal = Decimal(
                        event_object_data.get("amount")
                    ) / Decimal("100")
        else:
            if event_object_data.get("amount") is not None:
                refunded_amount_decimal = Decimal(
                    event_object_data.get("amount")
                ) / Decimal("100")

    return {
        "refunded_amount_decimal": refunded_amount_decimal,
        "stripe_refund_id": stripe_refund_id,
        "refund_status": refund_status,
        "charge_id": charge_id,
        "is_charge_object": is_charge_object,
        "is_refund_object": is_refund_object,
    }
