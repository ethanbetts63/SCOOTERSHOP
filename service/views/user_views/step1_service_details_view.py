import uuid
import datetime
from django.shortcuts import redirect
from django.views import View
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone

from service.forms import ServiceDetailsForm
from service.models import (
    TempServiceBooking,
    ServiceProfile,
    ServiceSettings,
    BlockedServiceDate,
)
from service.utils.booking_protection import check_and_manage_recent_booking_flag


class Step1ServiceDetailsView(View):
    template_name = "service/step1_service_details_include.html"

    def post(self, request, *args, **kwargs):

        redirect_response = check_and_manage_recent_booking_flag(request)
        if redirect_response:
            return redirect_response

        if "service_booking_reference" in request.session:
            del request.session["service_booking_reference"]

        form = ServiceDetailsForm(request.POST)
        service_settings = ServiceSettings.objects.first()

        errors_exist = False

        if form.is_valid():
            service_type = form.cleaned_data["service_type"]
            service_date = form.cleaned_data["service_date"]

            now_in_perth = timezone.localtime(timezone.now())

            if service_settings and service_settings.booking_advance_notice is not None:
                min_allowed_service_date = (
                    now_in_perth
                    + datetime.timedelta(days=service_settings.booking_advance_notice)
                ).date()

                if service_date < min_allowed_service_date:
                    messages.error(
                        request,
                        f"Service date must be at least {service_settings.booking_advance_notice} days from now. Please choose a later date.",
                    )
                    errors_exist = True

            if service_settings and service_settings.booking_open_days:
                day_names = {
                    0: "Monday",
                    1: "Tuesday",
                    2: "Wednesday",
                    3: "Thursday",
                    4: "Friday",
                    5: "Saturday",
                    6: "Sunday",
                }
                selected_day_of_week_full = day_names.get(service_date.weekday())
                open_days_list = [
                    d.strip() for d in service_settings.booking_open_days.split(",")
                ]

                abbreviated_day_names = {
                    0: "Mon",
                    1: "Tue",
                    2: "Wed",
                    3: "Thu",
                    4: "Fri",
                    5: "Sat",
                    6: "Sun",
                }
                selected_day_of_week_abbr = abbreviated_day_names.get(
                    service_date.weekday()
                )

                if selected_day_of_week_abbr not in open_days_list:
                    messages.error(
                        request,
                        f"Services are not available on {selected_day_of_week_full}s.",
                    )
                    errors_exist = True

            blocked_dates_overlap = BlockedServiceDate.objects.filter(
                start_date__lte=service_date, end_date__gte=service_date
            ).exists()
            if blocked_dates_overlap:
                messages.error(
                    request,
                    "Selected service date overlaps with a blocked service period.",
                )
                errors_exist = True

            if errors_exist:
                return redirect("core:index")

            temp_booking = None

            temp_booking_uuid_from_session = request.session.get(
                "temp_service_booking_uuid"
            )

            if temp_booking_uuid_from_session:
                try:

                    temp_booking = TempServiceBooking.objects.get(
                        session_uuid=temp_booking_uuid_from_session
                    )
                except TempServiceBooking.DoesNotExist:

                    temp_booking = None

            service_profile_for_temp_booking = None
            customer_motorcycles_exist = False
            if request.user.is_authenticated:
                try:

                    service_profile_for_temp_booking = request.user.service_profile

                    if service_profile_for_temp_booking.customer_motorcycles.exists():
                        customer_motorcycles_exist = True
                except ServiceProfile.DoesNotExist:
                    pass

            try:
                if temp_booking:

                    temp_booking.service_type = service_type
                    temp_booking.service_date = service_date
                    if service_profile_for_temp_booking:
                        temp_booking.service_profile = service_profile_for_temp_booking
                    else:
                        temp_booking.service_profile = None
                    temp_booking.save()
                    messages.success(
                        request,
                        "Service details updated. Please choose your motorcycle.",
                    )
                else:

                    temp_booking = TempServiceBooking.objects.create(
                        session_uuid=uuid.uuid4(),
                        service_type=service_type,
                        service_date=service_date,
                        service_profile=service_profile_for_temp_booking,
                    )

                    request.session["temp_service_booking_uuid"] = str(
                        temp_booking.session_uuid
                    )
                    messages.success(
                        request,
                        "Service details selected. Please choose your motorcycle.",
                    )

                if request.user.is_authenticated and customer_motorcycles_exist:

                    redirect_url = (
                        reverse("service:service_book_step2")
                        + f"?temp_booking_uuid={temp_booking.session_uuid}"
                    )
                else:

                    redirect_url = (
                        reverse("service:service_book_step3")
                        + f"?temp_booking_uuid={temp_booking.session_uuid}"
                    )

                return redirect(redirect_url)

            except Exception as e:

                messages.error(
                    request,
                    f"An unexpected error occurred while saving your selection: {e}",
                )
                return redirect("core:index")

        else:

            for field, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, f"Error in {field}: {error}")
            return redirect("core:index")
