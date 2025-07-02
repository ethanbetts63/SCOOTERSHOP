from django.views.generic import View
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from service.models import ServiceBooking


class AdminServiceBookingDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):

    template_name = "service/admin_service_booking_delete.html"

    def test_func(self):

        return self.request.user.is_staff or self.request.user.is_superuser

    def get(self, request, pk, *args, **kwargs):

        booking = get_object_or_404(ServiceBooking, pk=pk)
        return render(request, self.template_name, {"booking": booking})

    def post(self, request, pk, *args, **kwargs):

        booking = get_object_or_404(ServiceBooking, pk=pk)
        booking_ref = booking.service_booking_reference
        try:
            booking.delete()
            messages.success(
                request, f"Booking {booking_ref} has been successfully deleted."
            )
        except Exception as e:
            messages.error(
                request, f"An error occurred while deleting the booking: {e}"
            )

        return redirect(reverse_lazy("service:service_booking_management"))
