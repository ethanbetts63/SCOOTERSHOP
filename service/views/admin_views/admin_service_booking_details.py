from django.views.generic import DetailView
from service.mixins import AdminRequiredMixin
from service.models import ServiceBooking


class AdminServiceBookingDetailView(AdminRequiredMixin, DetailView):

    model = ServiceBooking
    template_name = "service/admin_service_booking_detail.html"
    context_object_name = "service_booking"

    def test_func(self):

        return self.request.user.is_staff

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["booking_pk"] = self.object.pk
        return context
