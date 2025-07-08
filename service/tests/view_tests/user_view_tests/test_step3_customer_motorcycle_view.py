from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django.contrib import messages
from service.models import TempServiceBooking, ServiceSettings
from service.forms.step3_customer_motorcycle_form import CustomerMotorcycleForm


class Step3CustomerMotorcycleView(View):
    template_name = "service/step3_customer_motorcycle.html"

    def dispatch(self, request, *args, **kwargs):
        temp_booking_uuid = request.session.get("temp_service_booking_uuid")

        if not temp_booking_uuid:
            return redirect(reverse("service:service"))

        try:
            self.temp_booking = TempServiceBooking.objects.get(
                session_uuid=temp_booking_uuid
            )
        except TempServiceBooking.DoesNotExist:
            request.session.pop("temp_service_booking_uuid", None)
            return redirect(reverse("service:service"))

        self.service_settings = ServiceSettings.objects.first()
        if not self.service_settings:
            messages.error(
                request,
                "Service settings are not configured. Please contact an administrator.",
            )
            return redirect(reverse("service:service"))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = None
        if self.temp_booking.customer_motorcycle:
            form = CustomerMotorcycleForm(
                instance=self.temp_booking.customer_motorcycle
            )
        else:
            form = CustomerMotorcycleForm()

        context = {
            "form": form,
            "temp_booking": self.temp_booking,
            "step": 3,
            "total_steps": 7,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = None
        motorcycle_instance = self.temp_booking.customer_motorcycle

        if motorcycle_instance:
            form = CustomerMotorcycleForm(
                request.POST, request.FILES, instance=motorcycle_instance
            )
        else:
            form = CustomerMotorcycleForm(request.POST, request.FILES)

        if form.is_valid():
            customer_motorcycle = form.save(commit=False)

            if request.user.is_authenticated and self.temp_booking.service_profile:
                customer_motorcycle.service_profile = self.temp_booking.service_profile

            customer_motorcycle.save()

            self.temp_booking.customer_motorcycle = customer_motorcycle
            self.temp_booking.save()

            return redirect(reverse("service:service_book_step4"))
        else:
            context = {
                "form": form,
                "temp_booking": self.temp_booking,

                "step": 3,
                "total_steps": 7,
            }
            return render(request, self.template_name, context)
