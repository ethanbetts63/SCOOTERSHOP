from service.mixins import AdminRequiredMixin
from django.shortcuts import render
from django.views import View

from service.models import ServiceBooking


class ServiceBookingManagementView(AdminRequiredMixin, View):

    template_name = "service/service_booking_management.html"

    def get(self, request, *args, **kwargs):

        bookings = ServiceBooking.objects.select_related('service_profile', 'customer_motorcycle', 'service_type').all().order_by("-dropoff_date")

        context = {
            "page_title": "Manage Service Bookings",
            "bookings": bookings,
            "active_tab": "service_bookings",
        }
        return render(request, self.template_name, context)
