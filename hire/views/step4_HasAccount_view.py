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
            user=request.user,
            initial={
                "name": request.user.get_full_name(),
                "email": request.user.email,
            }
        )

        context = {
            "form": form,
            "temp_booking": temp_booking,  # Add temp_booking to the context
        }
        return render(request, "hire/step4_has_account.html", context)

    def post(self, request, *args, **kwargs):
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(
                request, "Your booking session has expired. Please start again."
            )
            return redirect("hire:step2_choose_bike")

        form = Step4HasAccountForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            # 1. Get or create DriverProfile
            driver_profile, created = DriverProfile.objects.get_or_create(
                user=request.user
            )

            # 2. Update DriverProfile fields
            driver_profile.name = form.cleaned_data["name"]
            driver_profile.email = form.cleaned_data["email"]
            driver_profile.phone_number = form.cleaned_data["phone_number"]
            driver_profile.address_line_1 = form.cleaned_data["address_line_1"]
            driver_profile.address_line_2 = form.cleaned_data["address_line_2"]
            driver_profile.city = form.cleaned_data["city"]
            driver_profile.state = form.cleaned_data["state"]
            driver_profile.post_code = form.cleaned_data["post_code"]
            driver_profile.country = form.cleaned_data["country"]
            driver_profile.date_of_birth = form.cleaned_data["date_of_birth"]
            driver_profile.is_australian_resident = form.cleaned_data["is_australian_resident"]
            driver_profile.license_number = form.cleaned_data["license_number"]
            driver_profile.license_issuing_country = form.cleaned_data["license_issuing_country"]
            driver_profile.license_expiry_date = form.cleaned_data["license_expiry_date"]
            driver_profile.license_photo = form.cleaned_data["license_photo"]
            driver_profile.international_license_photo = form.cleaned_data["international_license_photo"]
            driver_profile.passport_photo = form.cleaned_data["passport_photo"]
            driver_profile.passport_number = form.cleaned_data["passport_number"]
            driver_profile.passport_expiry_date = form.cleaned_data["passport_expiry_date"]
            driver_profile.id_image = form.cleaned_data["id_image"]
            driver_profile.international_id_image = form.cleaned_data["international_id_image"]
            driver_profile.save()

            # 3. Save DriverProfile to TempHireBooking
            temp_booking.driver_profile = driver_profile
            temp_booking.save()

            return redirect("hire:step5_summary_payment_options")
        else:
            context = {
                "form": form,
                "temp_booking": temp_booking, # Ensure temp_booking is in the context on form error too
            }
            return render(request, "hire/step4_has_account.html", context)

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