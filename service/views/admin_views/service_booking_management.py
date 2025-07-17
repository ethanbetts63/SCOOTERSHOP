from service.mixins import AdminRequiredMixin
from django.shortcuts import render
from django.views import View

from service.models import ServiceBooking


from django.db.models import Q


class ServiceBookingManagementView(AdminRequiredMixin, View):
    template_name = "service/service_booking_management.html"

    def get(self, request, *args, **kwargs):
        search_term = request.GET.get("q", "")
        bookings = ServiceBooking.objects.select_related(
            "service_profile", "customer_motorcycle", "service_type"
        ).all()

        if search_term:
            bookings = bookings.filter(
                Q(service_profile__name__icontains=search_term)
                | Q(service_booking_reference__icontains=search_term)
                | Q(customer_motorcycle__rego__icontains=search_term)
                | Q(customer_motorcycle__brand__icontains=search_term)
                | Q(customer_motorcycle__model__icontains=search_term)
                | Q(booking_status__icontains=search_term)
            )

        bookings = bookings.order_by("-dropoff_date")

        context = {
            "page_title": "Manage Service Bookings",
            "bookings": bookings,
            "active_tab": "service_bookings",
            "search_term": search_term,
        }
        return render(request, self.template_name, context)
