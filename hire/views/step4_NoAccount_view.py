from django.shortcuts import render, redirect
from django.views import View
from hire.forms import Step4NoAccountForm
from hire.models import TempHireBooking, DriverProfile
from django.contrib import messages
from dashboard.models import HireSettings
from hire.hire_pricing import calculate_booking_grand_total


class NoAccountView(View):

    def get(self, request, *args, **kwargs):
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(
                request, "Your booking session has expired. Please start again."
            )
            return redirect("hire:step2_choose_bike")

        form = Step4NoAccountForm(temp_booking=temp_booking)
        context = {
            "form": form,
            "temp_booking": temp_booking,
        }
        return render(
            request, "hire/step4_no_account.html", context
        )

    def post(self, request, *args, **kwargs):
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(
                request, "Your booking session has expired. Please start again."
            )
            return redirect("hire:step2_choose_bike")

        form = Step4NoAccountForm(request.POST, request.FILES, temp_booking=temp_booking)
        if form.is_valid():
            driver_profile = form.save(commit=False)
            driver_profile.save()

            temp_booking.driver_profile = driver_profile
            
            hire_settings = HireSettings.objects.first()
            if hire_settings:
                calculated_prices = calculate_booking_grand_total(temp_booking, hire_settings)
                temp_booking.total_hire_price = calculated_prices['motorcycle_price']
                temp_booking.total_package_price = calculated_prices['package_price']
                temp_booking.total_addons_price = calculated_prices['addons_total_price']
                temp_booking.grand_total = calculated_prices['grand_total']
            else:
                messages.warning(request, "Hire settings not found. Cannot calculate accurate booking prices.")

            temp_booking.save()

            messages.success(request, "Driver details saved successfully.")
            return redirect("hire:step5_summary_payment_options")
        else:
            context = {
                "form": form,
                "temp_booking": temp_booking,
            }
            messages.error(request, "Please correct the errors below.")
            return render(
                request, "hire/step4_no_account.html", context
            )

    def _get_temp_booking(self, request):
        temp_booking_id = request.session.get("temp_booking_id")
        temp_booking_uuid = request.session.get("temp_booking_uuid")
        if temp_booking_id and temp_booking_uuid:
            try:
                return TempHireBooking.objects.get(
                    id=temp_booking_id, session_uuid=temp_booking_uuid
                )
            except TempHireBooking.DoesNotExist:
                return None
        return None
