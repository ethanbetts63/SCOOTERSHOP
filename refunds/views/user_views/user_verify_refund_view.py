from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
import uuid
from decimal import Decimal
from django.conf import settings
from django.http import Http404
from refunds.models.RefundRequest import RefundRequest
from refunds.utils.service_refund_calc import calculate_service_refund_amount
from refunds.utils.sales_refund_calc import calculate_sales_refund_amount
from mailer.utils import send_templated_email
from service.models import ServiceProfile
from inventory.models import SalesProfile


def _convert_decimals_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: _convert_decimals_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_decimals_to_float(elem) for elem in obj]
    else:
        return obj


class UserVerifyRefundView(View):
    def get(self, request, *args, **kwargs):
        token_str = request.GET.get("token")

        if not token_str:
            messages.error(request, "Verification link is missing a token.")
            return redirect(reverse("core:index"))

        try:
            verification_token = uuid.UUID(token_str)
        except ValueError:
            messages.error(request, "Invalid verification token format.")
            return redirect(reverse("core:index"))

        try:
            refund_request = get_object_or_404(
                RefundRequest, verification_token=verification_token
            )

            if refund_request.status != "unverified":
                messages.info(
                    request,
                    "This refund request has already been verified or processed.",
                )
                return redirect(reverse("payments:user_verified_refund"))

            token_validity_hours = 24
            if (timezone.now() - refund_request.token_created_at) > timedelta(
                hours=token_validity_hours
            ):
                messages.error(
                    request,
                    "The verification link has expired. Please submit a new refund request.",
                )
                return redirect(reverse("payments:user_refund_request"))

            refund_request.status = "pending"
            refund_request.save()

            calculated_refund_result = {
                "entitled_amount": Decimal("0.00"),
                "details": "No calculation performed.",
            }
            booking_reference_for_email = "N/A"
            booking_object = None
            customer_profile_object = None

            admin_link_name = "payments:edit_refund_request"

            if refund_request.service_booking:
                calculated_refund_result = calculate_service_refund_amount(
                    booking=refund_request.service_booking,
                    cancellation_datetime=refund_request.requested_at,
                )
                booking_reference_for_email = (
                    refund_request.service_booking.service_booking_reference
                )
                booking_object = refund_request.service_booking
                customer_profile_object = refund_request.service_profile
                booking_type_for_details = "service"
            elif refund_request.sales_booking:
                calculated_refund_result = calculate_sales_refund_amount(
                    booking=refund_request.sales_booking,
                    cancellation_datetime=refund_request.requested_at,
                )
                booking_reference_for_email = (
                    refund_request.sales_booking.sales_booking_reference
                )
                booking_object = refund_request.sales_booking
                customer_profile_object = refund_request.sales_profile
                booking_type_for_details = "sales"
            else:
                booking_type_for_details = "unknown"

            calculated_refund_amount = calculated_refund_result.get(
                "entitled_amount", Decimal("0.00")
            )

            json_compatible_calculation_details = _convert_decimals_to_float(
                calculated_refund_result
            )

            refund_request.refund_calculation_details = {
                "calculated_amount": float(calculated_refund_amount),
                "cancellation_datetime": refund_request.requested_at.isoformat(),
                "booking_type": booking_type_for_details,
                "full_calculation_details": json_compatible_calculation_details,
            }
            refund_request.amount_to_refund = calculated_refund_amount
            refund_request.save()

            admin_refund_link = request.build_absolute_uri(
                reverse(admin_link_name, args=[refund_request.pk])
            )

            admin_email_context = {
                "refund_request": refund_request,
                "calculated_refund_amount": calculated_refund_amount,
                "admin_refund_link": admin_refund_link,
                "booking_reference": booking_reference_for_email,
            }

            admin_recipient_list = [
                getattr(settings, "ADMIN_EMAIL", settings.DEFAULT_FROM_EMAIL)
            ]
            if (
                not admin_recipient_list
                or admin_recipient_list[0] == settings.DEFAULT_FROM_EMAIL
            ):
                admin_recipient_list = [settings.DEFAULT_FROM_EMAIL]

            send_templated_email(
                recipient_list=admin_recipient_list,
                subject=f"VERIFIED Refund Request for Booking {booking_reference_for_email} (ID: {refund_request.pk})",
                template_name="admin_refund_request_notification.html",
                context=admin_email_context,
                booking=booking_object,
                service_profile=(
                    customer_profile_object
                    if isinstance(customer_profile_object, ServiceProfile)
                    else None
                ),
                sales_profile=(
                    customer_profile_object
                    if isinstance(customer_profile_object, SalesProfile)
                    else None
                ),
            )

            messages.success(
                request, "Your refund request has been successfully verified!"
            )
            return redirect(reverse("payments:user_verified_refund"))

        except Http404:
            messages.error(
                request, "The refund request associated with this token does not exist."
            )
            return redirect(reverse("core:index"))
        except Exception as e:
            messages.error(
                request, f"An unexpected error occurred during verification: {e}"
            )
            return redirect(reverse("core:index"))
