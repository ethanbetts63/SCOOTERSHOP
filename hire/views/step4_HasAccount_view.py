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

        # Get the driver profile associated with the current temporary booking
        # This is the key change: use temp_booking.driver_profile for initial data
        driver_profile_instance = temp_booking.driver_profile

        # Initialize the form, passing the driver_profile_instance if it exists.
        # The form's __init__ method should then use this instance to pre-populate fields.
        form = Step4HasAccountForm(user=request.user, instance=driver_profile_instance)

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

        # Get the driver profile associated with the current temporary booking
        # This is important for updating an existing profile rather than creating a new one
        driver_profile_instance = temp_booking.driver_profile

        # Initialize the form with POST data, files, and the existing instance
        form = Step4HasAccountForm(request.POST, request.FILES, user=request.user, instance=driver_profile_instance)

        if form.is_valid():
            # Save the form, which will update the existing driver_profile_instance
            # or create a new one if driver_profile_instance was None (though it should not be if user is logged in)
            driver_profile = form.save(commit=False) # Use commit=False to allow linking user before saving
            driver_profile.user = request.user # Ensure the user is linked
            driver_profile.save()

            # Link the saved driver_profile to the temporary booking
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
            return render(request, "hire/step4_has_account.html", context)

    def _get_temp_booking(self, request):
        temp_booking_id = request.session.get("temp_booking_id")
        temp_booking_uuid = request.session.get("temp_booking_uuid")
        if temp_booking_id and temp_booking_uuid:
            try:
                return TempHireBooking.objects.get(
                    id=temp_booking_id,
                    session_uuid=temp_booking_uuid
                )
            except TempHireBooking.DoesNotExist:
                return None
        return None
