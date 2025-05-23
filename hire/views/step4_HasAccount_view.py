from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from hire.forms import Step4HasAccountForm
from hire.models import TempHireBooking, DriverProfile
from django.contrib import messages


class HasAccountView(LoginRequiredMixin, View):
    """
    Handles Step 4 for logged-in users.
    """

    def get(self, request, *args, **kwargs):
        print(f"DEBUG: HasAccountView GET - User: {request.user}")
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(
                request, "Your booking session has expired. Please start again."
            )
            return redirect("hire:step2_choose_bike")

        print(f"DEBUG: HasAccountView GET - temp_booking.driver_profile: {temp_booking.driver_profile}")

        # Try to get the existing driver profile for the user.
        # If it doesn't exist, create a new instance without saving it to the DB yet.
        # This prevents the NOT NULL constraint error on GET for new profiles.
        driver_profile_instance = None
        try:
            driver_profile_instance = DriverProfile.objects.get(user=request.user)
            print(f"DEBUG: HasAccountView GET - Retrieved existing DriverProfile: {driver_profile_instance}")
        except DriverProfile.DoesNotExist:
            # If no profile exists, create a new unsaved instance.
            # The form will then handle populating and saving it.
            driver_profile_instance = DriverProfile(user=request.user)
            print("DEBUG: HasAccountView GET - Created new unsaved DriverProfile instance.")

        # Pass the instance (either existing or new unsaved) to the form
        form = Step4HasAccountForm(user=request.user, instance=driver_profile_instance, temp_booking=temp_booking)

        context = {
            "form": form,
            "temp_booking": temp_booking,
        }
        return render(request, "hire/step4_has_account.html", context)

    def post(self, request, *args, **kwargs):
        print(f"DEBUG: HasAccountView POST - User: {request.user}")
        temp_booking = self._get_temp_booking(request)
        if not temp_booking:
            messages.error(
                request, "Your booking session has expired. Please start again."
            )
            return redirect("hire:step2_choose_bike")

        print(f"DEBUG: HasAccountView POST - temp_booking.driver_profile: {temp_booking.driver_profile}")
        
        # Always try to get the existing driver profile for the user.
        # If it doesn't exist, create a new instance (which the form will then populate and save).
        driver_profile_instance = None
        try:
            driver_profile_instance = DriverProfile.objects.get(user=request.user)
            print(f"DEBUG: HasAccountView POST - Retrieved existing DriverProfile for POST: {driver_profile_instance}")
        except DriverProfile.DoesNotExist:
            driver_profile_instance = DriverProfile(user=request.user)
            print("DEBUG: HasAccountView POST - Created new unsaved DriverProfile instance for POST.")


        form = Step4HasAccountForm(request.POST, request.FILES, user=request.user, instance=driver_profile_instance, temp_booking=temp_booking)

        if form.is_valid():
            driver_profile = form.save(commit=False)
            driver_profile.user = request.user  # Ensure user is linked
            driver_profile.save() # Save the driver profile after all fields are validated and set

            temp_booking.driver_profile = driver_profile
            print(f"DEBUG: HasAccountView POST - temp_booking.driver_profile after setting: {temp_booking.driver_profile}")
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
