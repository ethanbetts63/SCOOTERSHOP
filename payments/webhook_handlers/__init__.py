# payments/webhook_handlers/__init__.py

# Import handler functions from specific files
from .hire_handlers import (
    handle_hire_booking_succeeded,
)
from .refund_handlers import (
    handle_booking_refunded,
    handle_booking_refund_updated,
)
from .service_handlers import (
    handle_service_booking_succeeded,
)

# Define the WEBHOOK_HANDLERS dictionary
# This dictionary maps booking types to a further dictionary of event types and their respective handlers.
WEBHOOK_HANDLERS = {
    'hire_booking': {
        'payment_intent.succeeded': handle_hire_booking_succeeded,
        'charge.refunded': handle_booking_refunded, # Handlers are now imported from refund_handlers.py
        'charge.refund.updated': handle_booking_refund_updated, # Handlers are now imported from refund_handlers.py
    },
    'service_booking': {
        'payment_intent.succeeded': handle_service_booking_succeeded,
        # Add handlers for charge-related events for service bookings
        'charge.refunded': handle_booking_refunded, # Reusing hire_booking's refund handler, assuming it's generic enough
        'charge.refund.updated': handle_booking_refund_updated, # Reusing hire_booking's refund update handler, assuming it's generic enough
        # NEW: Add a handler for charge.succeeded if you expect it for service bookings
        # It's typical for a charge.succeeded to be handled, even if payment_intent.succeeded is the primary.
        # This will prevent the "No handler found" log for charge.succeeded
        'charge.succeeded': handle_service_booking_succeeded, # Re-using the success handler for service bookings
    },
}

