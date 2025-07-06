from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django.contrib import messages
from decimal import Decimal
from django.conf import settings
import json
from service.forms.step5_payment_choice_and_terms_form import PaymentOptionForm
from service.models import TempServiceBooking, ServiceSettings, Servicefaq, ServiceTerms
from service.utils.convert_temp_service_booking import convert_temp_service_booking
from service.utils.get_drop_off_date_availability import get_drop_off_date_availability
from service.utils.calculate_service_total import calculate_service_total
from service.utils.calulcate_service_deposit import calculate_service_deposit
from service.utils.calculate_estimated_pickup_date import (
    calculate_estimated_pickup_date,
)
from mailer.utils import send_templated_email


class Step5PaymentDropoffAndTermsView(View):
    template_name = "service/step5_payment_dropoff_and_terms.html"
    form_class = PaymentOptionForm

    def _get_temp_booking(self, request):
        temp_service_booking_uuid = request.session.get("temp_service_booking_uuid")
        if not temp_service_booking_uuid:
            messages.error(
                request, "Your booking session has expired. Please start over."
            )
            return None, redirect(reverse("service:service"))

        try:
            temp_booking = TempServiceBooking.objects.select_related(
                "service_type", "customer_motorcycle", "service_profile"
            ).get(session_uuid=temp_service_booking_uuid)
            return temp_booking, None
        except TempServiceBooking.DoesNotExist:
            request.session.pop("temp_service_booking_uuid", None)
            messages.error(
                request, "Your booking session could not be found. Please start over."
            )
            return None, redirect(reverse("service:service"))

    def dispatch(self, request, *args, **kwargs):
        self.temp_booking, redirect_response = self._get_temp_booking(request)
        if redirect_response:
            return redirect_response

        if not self.temp_booking.service_profile:
            messages.warning(
                request, "Please complete your personal details first (Step 4)."
            )
            return redirect(reverse("service:service_book_step4"))

        self.service_settings = ServiceSettings.objects.first()
        if not self.service_settings:
            messages.error(
                request,
                "Service settings are not configured. Please contact an administrator.",
            )
            return redirect(reverse("service:service"))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = {
            "service_settings": self.service_settings,
            "temp_booking": self.temp_booking,
        }
        return kwargs

    def get_context_data(self, **kwargs):
        available_dropoff_dates = get_drop_off_date_availability(
            self.temp_booking, self.service_settings
        )
        service_faqs = Servicefaq.objects.filter(is_active=True)
        context = {
            "temp_booking": self.temp_booking,
            "service_settings": self.service_settings,
            "available_dropoff_dates_json": json.dumps(available_dropoff_dates),
            "get_times_url": reverse("service:get_available_dropoff_times_for_date"),
            "step": 5,
            "total_steps": 7,
            "is_same_day_dropoff_only": (
                self.service_settings.max_advance_dropoff_days == 0
            ),
            "service_faqs": service_faqs,
        }
        context.update(kwargs)
        return context

    def get(self, request, *args, **kwargs):
        initial_data = {
            "dropoff_date": self.temp_booking.dropoff_date,
            "dropoff_time": self.temp_booking.dropoff_time,
            "payment_method": self.temp_booking.payment_method,
        }
        if self.service_settings.max_advance_dropoff_days == 0:
            initial_data["dropoff_date"] = self.temp_booking.service_date
        form = self.form_class(initial=initial_data, **self.get_form_kwargs())
        context = self.get_context_data(form=form)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, **self.get_form_kwargs())

        if form.is_valid():
            active_terms = ServiceTerms.objects.filter(is_active=True).first()
            if not active_terms:
                messages.error(request, "No active service terms found. Please contact an administrator.")
                return redirect(reverse("service:service"))

            self.temp_booking.dropoff_date = form.cleaned_data["dropoff_date"]
            self.temp_booking.dropoff_time = form.cleaned_data["dropoff_time"]
            self.temp_booking.payment_method = form.cleaned_data["payment_method"]
            self.temp_booking.service_terms_version = active_terms
            self.temp_booking.save(
                update_fields=["dropoff_date", "dropoff_time", "payment_method", "service_terms_version"]
            )

            self.temp_booking.calculated_total = calculate_service_total(
                self.temp_booking
            )
            self.temp_booking.calculated_deposit_amount = calculate_service_deposit(
                self.temp_booking
            )
            calculate_estimated_pickup_date(self.temp_booking)
            self.temp_booking.save(
                update_fields=[
                    "calculated_total",
                    "calculated_deposit_amount",
                    "estimated_pickup_date",
                ]
            )

            messages.success(
                request, "Drop-off and payment details have been saved successfully."
            )

            if self.temp_booking.payment_method == "in_store_full":
                try:
                    final_service_booking = convert_temp_service_booking(
                        temp_booking=self.temp_booking,
                        payment_method=self.temp_booking.payment_method,
                        booking_payment_status="unpaid",
                        amount_paid_on_booking=Decimal("0.00"),
                        calculated_total_on_booking=self.temp_booking.calculated_total,
                    )
                    request.session["service_booking_reference"] = (
                        final_service_booking.service_booking_reference
                    )

                    user_email = final_service_booking.service_profile.email
                    if user_email:
                        try:
                            send_templated_email(
                                recipient_list=[user_email],
                                subject=f"Your Service Booking Confirmed! Ref: {final_service_booking.service_booking_reference}",
                                template_name="emails/user_service_booking_confirmation.html",
                                context={},
                                booking=final_service_booking,
                                profile=final_service_booking.service_profile,
                            )
                            messages.info(
                                request,
                                "Booking confirmed, but failed to send confirmation email.",
                            )
                        except Exception:
                            messages.warning(
                                request,
                                "Booking confirmed, but failed to send confirmation email.",
                            )
                    else:
                        messages.warning(
                            request,
                            "Booking confirmed, but no email address found to send confirmation.",
                        )

                    admin_email = getattr(settings, "ADMIN_EMAIL", "admin@example.com")
                    if admin_email:
                        try:
                            send_templated_email(
                                recipient_list=[admin_email],
                                subject=f"NEW SERVICE BOOKING: {final_service_booking.service_booking_reference} (In-Store Payment)",
                                template_name="emails/admin_service_booking_confirmation.html",
                                context={},
                                booking=final_service_booking,
                                profile=final_service_booking.service_profile,
                            )
                        except Exception:
                            pass

                    return redirect(reverse("service:service_book_step7"))

                except Exception as e:
                    messages.error(
                        request,
                        f"An error occurred while finalizing your booking: {e}. Please try again.",
                    )
                    return redirect(reverse("service:service_book_step5"))
            else:
                return redirect(reverse("service:service_book_step6"))

        else:
            messages.error(request, "Please correct the errors highlighted below.")
            context = self.get_context_data(form=form)
            return render(request, self.template_name, context)
