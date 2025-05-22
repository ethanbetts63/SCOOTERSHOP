# hire/views/step4_NoAccount_view.py
from django.shortcuts import render, redirect
from django.views import View
from hire.forms import Step4NoAccountForm
from hire.models import TempHireBooking, DriverProfile
from django.contrib import messages


class NoAccountView(View):
    """
    Handles Step 4 for anonymous users.
    """

    def get(self, request, *args, **kwargs):
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(
                request, "Your booking session has expired. Please start again."
            )
            return redirect("hire:step2_choose_bike")

        # Pass temp_booking to the form
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

        # Pass temp_booking to the form
        form = Step4NoAccountForm(request.POST, request.FILES, temp_booking=temp_booking)
        if form.is_valid():
            # Create DriverProfile
            driver_profile = form.save(commit=False) # Use commit=False to allow linking
            driver_profile.save() # Save the driver profile

            # Save DriverProfile to TempHireBooking
            temp_booking.driver_profile = driver_profile
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

