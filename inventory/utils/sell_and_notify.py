from inventory.models import SalesBooking
from mailer.utils.send_templated_email import send_templated_email
from django.conf import settings

def sell_and_notify(motorcycle):
    """
    Marks a motorcycle as sold and notifies users with non-deposit bookings.
    """
    print(f"[sell_and_notify] Marking motorcycle {motorcycle.id} as sold.")
    motorcycle.status = "sold"
    motorcycle.save()

    bookings_to_notify = SalesBooking.objects.filter(
        motorcycle=motorcycle, payment_status='unpaid'
    )
    print(f"[sell_and_notify] Found {bookings_to_notify.count()} non-deposit bookings to notify.")

    for booking in bookings_to_notify:
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
        print(f"[sell_and_notify] Attempting to send email to {recipient_email} with subject: {subject}")
        try:
            success = send_templated_email(
                recipient_list=[recipient_email],
                subject=subject,
                template_name="mailer/user_notify_sold.html",
                context=context,
                booking=booking,
                profile=booking.sales_profile,
            )
            if success:
                print(f"[sell_and_notify] Successfully sent email to {recipient_email}.")
            else:
                print(f"[sell_and_notify] Failed to send email to {recipient_email}.")
        except Exception as e:
            print(f"[sell_and_notify] An error occurred while sending email to {recipient_email}: {e}")
