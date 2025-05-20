# hire/views/step4_HasAccount_view.py
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from hire.forms import Step4HasAccountForm
from hire.models import TempHireBooking
from hire.models import DriverProfile
from django.contrib import messages


class HasAccountView(LoginRequiredMixin, View):
    """
    Handles Step 4 for logged-in users.
    """

    def get(self, request, *args, **kwargs):
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(
                request, "Your booking session has expired. Please start again."
            )
            return redirect("hire:step2_choose_bike")

        form = Step4HasAccountForm(
            initial={
                "name": request.user.get_full_name(),
                "email": request.user.email,
            }
        )

        return render(request, "hire/step4_has_account.html", {"form": form})

    def post(self, request, *args, **kwargs):
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(
                request, "Your booking session has expired. Please start again."
            )
            return redirect("hire:step2_choose_bike")

        form = Step4HasAccountForm(request.POST)
        if form.is_valid():
            # 1. Get or create DriverProfile
            driver_profile, created = DriverProfile.objects.get_or_create(
                user=request.user
            )

            # 2. Update DriverProfile fields
            driver_profile.name = form.cleaned_data["name"]
            driver_profile.email = form.cleaned_data["email"]
            # ... (rest of the fields)
            driver_profile.save()

            # 3. Save DriverProfile to TempHireBooking
            temp_booking.driver_profile = driver_profile
            temp_booking.save()

            return redirect("hire:step5_summary_payment_options")
        else:
            return render(request, "hire/step4_has_account.html", {"form": form})

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
