from inventory.models import SalesBooking
from mailer.utils.send_templated_email import send_templated_email
from django.conf import settings

def sell_and_notify(motorcycle):
    """
    Marks a motorcycle as sold and notifies users with non-deposit bookings.
    """
    motorcycle.status = "sold"
    motorcycle.save()

    bookings_to_notify = SalesBooking.objects.filter(
        motorcycle=motorcycle, payment_status='unpaid'
    )

    for booking in bookings_to_notify:
        user = booking.sales_profile.user
        context = {
            "user": user,
            "motorcycle": motorcycle,
        }
        send_templated_email(
            recipient_list=[user.email],
            subject=f"Update on your interest in the {motorcycle.title}",
            template_name="mailer/user_notify_sold.html",
            context=context,
            booking=booking,
            profile=booking.sales_profile,
        )
