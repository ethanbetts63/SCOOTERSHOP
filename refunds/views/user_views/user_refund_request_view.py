from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
import uuid
from refunds.forms.user_refund_request_form import RefundRequestForm
from mailer.utils import send_templated_email


class UserRefundRequestView(View):
    template_name = "refunds/user_refund_request.html"

    def get(self, request, *args, **kwargs):
        form = RefundRequestForm()
        context = {
            "form": form,
            "page_title": "Request a Refund",
            "intro_text": "Please enter your booking details to request a refund. An email will be sent to confirm your request.",
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = RefundRequestForm(request.POST)

        if form.is_valid():
            refund_request = form.save(commit=False)

            if not refund_request.verification_token:
                refund_request.verification_token = uuid.uuid4()
            if not refund_request.token_created_at:
                refund_request.token_created_at = timezone.now()

            refund_request.save()

            verification_link = request.build_absolute_uri(
                reverse("refunds:user_verify_refund")
                + f"?token={str(refund_request.verification_token)}"
            )

            refund_policy_link = request.build_absolute_uri(reverse("core:returns"))
            admin_email = getattr(settings, "DEFAULT_FROM_EMAIL", "admin@example.com")

            booking_reference_for_email = "N/A"
            booking_object = None
            customer_profile_object = None

            if refund_request.service_booking:
                booking_reference_for_email = (
                    refund_request.service_booking.service_booking_reference
                )
                booking_object = refund_request.service_booking
                customer_profile_object = refund_request.service_profile
            elif refund_request.sales_booking:
                booking_reference_for_email = (
                    refund_request.sales_booking.sales_booking_reference
                )
                booking_object = refund_request.sales_booking
                customer_profile_object = refund_request.sales_profile

            user_email_context = {
                "refund_request": refund_request,
                "verification_link": verification_link,
                "refund_policy_link": refund_policy_link,
                "admin_email": admin_email,
                "booking_reference": booking_reference_for_email,
                "SITE_DOMAIN": settings.SITE_DOMAIN,
                "SITE_SCHEME": settings.SITE_SCHEME,
            }

            send_templated_email(
                recipient_list=[refund_request.request_email],
                subject=f"Confirm Your Refund Request for Booking {booking_reference_for_email}",
                template_name="user_refund_request_verification.html",
                context=user_email_context,
                booking=booking_object,
                profile=customer_profile_object,
            )

            messages.success(
                request,
                "Your refund request has been submitted. Please check your email to confirm your request.",
            )
            return redirect(reverse("refunds:user_confirmation_refund_request"))

        else:
            context = {
                "form": form,
                "page_title": "Request a Refund",
                "intro_text": "Please correct the errors below and try again.",
            }
            return render(request, self.template_name, context)
