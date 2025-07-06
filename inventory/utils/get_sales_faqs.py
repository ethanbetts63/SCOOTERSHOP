from django.db.models import Q
from inventory.models import Salesfaq


def get_faqs_for_step(step_name: str):
    step_filter = Q(booking_step=step_name) | Q(booking_step="general")

    return Salesfaq.objects.filter(step_filter, is_active=True).order_by(
        "-booking_step", "display_order"
    )
