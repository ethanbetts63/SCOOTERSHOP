                                       

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
from .sales_handlers import (
    handle_sales_booking_succeeded,
)

WEBHOOK_HANDLERS = {
    'hire_booking': {
        'payment_intent.succeeded': handle_hire_booking_succeeded,
        'charge.refunded': handle_booking_refunded,
        'charge.refund.updated': handle_booking_refund_updated,
    },
    'service_booking': {
        'payment_intent.succeeded': handle_service_booking_succeeded,
        'charge.refunded': handle_booking_refunded,
        'charge.refund.updated': handle_booking_refund_updated,
        'charge.succeeded': handle_service_booking_succeeded,
    },
    'sales_booking': { 
        'payment_intent.succeeded': handle_sales_booking_succeeded,
        'charge.refunded': handle_booking_refunded, 
        'charge.refund.updated': handle_booking_refund_updated, 
    },
}
