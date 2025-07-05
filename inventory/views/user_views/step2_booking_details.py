from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.db import transaction
from django.contrib import messages
from django.conf import settings
from decimal import Decimal
import json
from inventory.utils.booking_protection import set_recent_booking_flag


from inventory.models import TempSalesBooking, InventorySettings, SalesTerms
from inventory.forms.sales_booking_appointment_form import BookingAppointmentForm
from inventory.utils.get_sales_appointment_date_info import (
    get_sales_appointment_date_info,
)
from inventory.utils.convert_temp_sales_booking import convert_temp_sales_booking
from inventory.utils.get_sales_faqs import get_faqs_for_step
from mailer.utils import send_templated_email


class Step2BookingDetailsView(View):
    template_name = "inventory/step2_booking_details.html"

    def get(self, request, *args, **kwargs):
        temp_booking_uuid = request.session.get("temp_sales_booking_uuid")

        if not temp_booking_uuid:
            messages.error(
                request,
                "Your booking session has expired or is invalid. Please start again.",
            )
            return redirect(reverse("core:index"))

        try:
            temp_booking = get_object_or_404(
                TempSalesBooking, session_uuid=temp_booking_uuid
            )
        except Exception as e:
            messages.error(
                request,
                f"Your booking session could not be found or is invalid. Error: {e}",
            )
            return redirect(reverse("core:index"))

        inventory_settings = InventorySettings.objects.first()
        if not inventory_settings:
            messages.error(
                request,
                "Inventory settings are not configured. Please contact support.",
            )
            return redirect(reverse("core:index"))

        initial_data = {
            "request_viewing": "yes" if temp_booking.request_viewing else "no",
            "appointment_date": temp_booking.appointment_date,
            "appointment_time": temp_booking.appointment_time,
            "customer_notes": temp_booking.customer_notes,
            "terms_accepted": temp_booking.terms_accepted,
        }

        form = BookingAppointmentForm(
            initial=initial_data,
            deposit_required_for_flow=temp_booking.deposit_required_for_flow,
            inventory_settings=inventory_settings,
        )

        min_date_obj, max_date_obj, blocked_dates_list = (
            get_sales_appointment_date_info(
                inventory_settings, temp_booking.deposit_required_for_flow
            )
        )

        min_date_str = min_date_obj.strftime("%Y-%m-%d")
        max_date_str = max_date_obj.strftime("%Y-%m-%d")
        blocked_dates_json = json.dumps(blocked_dates_list)

        context = {
            "form": form,
            "temp_booking": temp_booking,
            "inventory_settings": inventory_settings,
            "min_appointment_date": min_date_str,
            "max_appointment_date": max_date_str,
            "blocked_appointment_dates_json": blocked_dates_json,
            "sales_faqs": get_faqs_for_step("step2"),
            "faq_title": "Booking & Appointment Questions",
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        temp_booking_uuid = request.session.get("temp_sales_booking_uuid")
        print(f"DEBUG: Step2 POST - Initial temp_sales_booking_uuid: {temp_booking_uuid}")

        if not temp_booking_uuid:
            print("DEBUG: Step2 POST - No temp_sales_booking_uuid found, redirecting to index.")
            messages.error(
                request,
                "Your booking session has expired or is invalid. Please start again.",
            )
            return redirect(reverse("core:index"))

        try:
            temp_booking = get_object_or_404(
                TempSalesBooking, session_uuid=temp_booking_uuid
            )
        except Exception as e:
            messages.error(
                request,
                f"Your booking session could not be found or is invalid. Error: {e}",
            )
            return redirect(reverse("core:index"))

        inventory_settings = InventorySettings.objects.first()
        if not inventory_settings:
            messages.error(
                request,
                "Inventory settings are not configured. Please contact support.",
            )
            return redirect(reverse("core:index"))

        form = BookingAppointmentForm(
            request.POST,
            deposit_required_for_flow=temp_booking.deposit_required_for_flow,
            inventory_settings=inventory_settings,
        )

        if form.is_valid():
            print("DEBUG: Step2 POST - Form is valid.")
            with transaction.atomic():
                active_terms = SalesTerms.objects.filter(is_active=True).first()
                if not active_terms:
                    messages.error(request, "No active sales terms found. Please contact an administrator.")
                    return redirect(reverse("core:index"))

                customer_notes = form.cleaned_data.get("customer_notes")
                request_viewing = form.cleaned_data.get("request_viewing")
                appointment_date = form.cleaned_data.get("appointment_date")
                appointment_time = form.cleaned_data.get("appointment_time")
                terms_accepted = form.cleaned_data.get("terms_accepted")

                temp_booking.customer_notes = customer_notes
                temp_booking.request_viewing = request_viewing
                temp_booking.appointment_date = appointment_date
                temp_booking.appointment_time = appointment_time
                temp_booking.terms_accepted = terms_accepted
                temp_booking.sales_terms_version = active_terms
                temp_booking.save()

                if temp_booking.deposit_required_for_flow:
                    print("DEBUG: Step2 POST - Deposit required, redirecting to step3_payment.")
                    messages.success(
                        request, "Booking details saved. Proceed to payment."
                    )
                    return redirect(reverse("inventory:step3_payment"))
                else:
                    print("DEBUG: Step2 POST - No deposit required, converting to sales booking and redirecting to step4_confirmation.")
                    converted_sales_booking = convert_temp_sales_booking(
                        temp_booking=temp_booking,
                        booking_payment_status="unpaid",
                        amount_paid_on_booking=Decimal("0.00"),
                        stripe_payment_intent_id=None,
                        payment_obj=None,
                    )

                    if converted_sales_booking.appointment_date:
                        template_name = "user_sales_booking_confirmation.html"
                        subject = f"Your Motorcycle Appointment Request - {converted_sales_booking.sales_booking_reference}"
                    else:
                        template_name = "user_sales_enquiry_confirmation.html"
                        subject = f"Your Motorcycle Enquiry Received - {converted_sales_booking.sales_booking_reference}"

                    email_context = {
                        "booking": converted_sales_booking,
                        "sales_profile": converted_sales_booking.sales_profile,
                        "is_deposit_confirmed": False,
                    }
                    user_email = converted_sales_booking.sales_profile.email

                    try:
                        send_templated_email(
                            recipient_list=[user_email],
                            subject=subject,
                            template_name=template_name,
                            context=email_context,
                            booking=converted_sales_booking,
                            profile=converted_sales_booking.sales_profile,
                        )
                    except Exception:
                        pass

                    if settings.ADMIN_EMAIL:
                        try:
                            send_templated_email(
                                recipient_list=[settings.ADMIN_EMAIL],
                                subject=f"New Sales Enquiry (Online) - {converted_sales_booking.sales_booking_reference}",
                                template_name="admin_sales_booking_confirmation.html",
                                context=email_context,
                                booking=converted_sales_booking,
                                profile=converted_sales_booking.sales_profile,
                            )
                        except Exception:
                            pass

                    if "temp_sales_booking_uuid" in request.session:
                        del request.session["temp_sales_booking_uuid"]

                    request.session["current_sales_booking_reference"] = (
                        converted_sales_booking.sales_booking_reference
                    )
                    set_recent_booking_flag(request)
                    messages.success(
                        request,
                        "Your enquiry has been submitted. We will get back to you shortly!",
                    )
                    return redirect(reverse("inventory:step4_confirmation"))
        else:
            print(f"DEBUG: Step2 POST - Form is NOT valid. Errors: {form.errors.as_json()}")
            min_date_obj, max_date_obj, blocked_dates_list = (
                get_sales_appointment_date_info(
                    inventory_settings, temp_booking.deposit_required_for_flow
                )
            )
            min_date_str = min_date_obj.strftime("%Y-%m-%d")
            max_date_str = max_date_obj.strftime("%Y-%m-%d")
            blocked_dates_json = json.dumps(blocked_dates_list)

            context = {
                "form": form,
                "temp_booking": temp_booking,
                "inventory_settings": inventory_settings,
                "min_appointment_date": min_date_str,
                "max_appointment_date": max_date_str,
                "blocked_appointment_dates_json": blocked_dates_json,
                "sales_faqs": get_faqs_for_step("step2"),
                "faq_title": "Booking & Appointment Questions",
            }
            messages.error(request, "Please correct the errors below.")
            return render(request, self.template_name, context)
