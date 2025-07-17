from inventory.models import SalesBooking
from mailer.utils.send_templated_email import send_templated_email
from django.conf import settings


def sell_and_notify(motorcycle):
    motorcycle.status = "sold"
    motorcycle.save()
    bookings_to_notify = SalesBooking.objects.filter(
        motorcycle=motorcycle, payment_status="unpaid"
    )

    for booking in bookings_to_notify:
        booking.booking_status = "cancelled"
        booking.save()
        user = booking.sales_profile.user
        recipient_email = user.email
        subject = f"Update on your interest in the {motorcycle.title}"
        context = {
            "user": user,
            "motorcycle": motorcycle,
            "booking": booking,
            "profile": booking.sales_profile,
            "SITE_DOMAIN": settings.SITE_DOMAIN,
            "SITE_SCHEME": settings.SITE_SCHEME,
        }
        try:
            success = send_templated_email(
                recipient_list=[recipient_email],
                subject=subject,
                template_name="user_notify_sold.html",
                context=context,
                booking=booking,
                profile=booking.sales_profile,
            )
            if success:
                pass
        except Exception as e:
            pass
