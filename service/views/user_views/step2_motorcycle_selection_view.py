from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from service.forms import MotorcycleSelectionForm, ADD_NEW_MOTORCYCLE_OPTION
from service.models import (
    TempServiceBooking,
    CustomerMotorcycle,
    Servicefaq,
)


class Step2MotorcycleSelectionView(LoginRequiredMixin, View):
    template_name = "service/step2_motorcycle_selection.html"

    def dispatch(self, request, *args, **kwargs):
        session_uuid = request.session.get("temp_service_booking_uuid")

        if not session_uuid:
            return redirect(reverse("service:service"))

        try:
            self.temp_booking = TempServiceBooking.objects.get(
                session_uuid=session_uuid
            )
        except TempServiceBooking.DoesNotExist:
            request.session.pop("temp_service_booking_uuid", None)
            return redirect(reverse("service:service"))

        if not self.temp_booking.service_profile:
            return redirect(reverse("service:service_book_step3"))

        self.service_profile = self.temp_booking.service_profile

        has_motorcycles = self.service_profile.customer_motorcycles.exists()

        if not has_motorcycles:
            return redirect(reverse("service:service_book_step3"))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = MotorcycleSelectionForm(service_profile=self.service_profile)
        service_faqs = Servicefaq.objects.filter(is_active=True)
        context = {
            "form": form,
            "temp_booking": self.temp_booking,
            "service_faqs": service_faqs,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = MotorcycleSelectionForm(
            service_profile=self.service_profile, data=request.POST
        )

        if form.is_valid():
            selected_motorcycle_value = form.cleaned_data["selected_motorcycle"]

            if selected_motorcycle_value == ADD_NEW_MOTORCYCLE_OPTION:
                return redirect(reverse("service:service_book_step3"))
            else:
                try:
                    motorcycle_id = int(selected_motorcycle_value)
                    motorcycle = get_object_or_404(
                        CustomerMotorcycle,
                        pk=motorcycle_id,
                        service_profile=self.service_profile,
                    )
                    self.temp_booking.customer_motorcycle = motorcycle
                    self.temp_booking.save()
                    return redirect(reverse("service:service_book_step4"))
                except (ValueError, CustomerMotorcycle.DoesNotExist):
                    form.add_error(
                        "selected_motorcycle", "Invalid motorcycle selection."
                    )

        service_faqs = Servicefaq.objects.filter(is_active=True)
        context = {
            "form": form,
            "temp_booking": self.temp_booking,
            "service_faqs": service_faqs,
        }
        return render(request, self.template_name, context)
