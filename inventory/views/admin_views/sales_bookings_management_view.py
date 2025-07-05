from django.db.models import Q
from django.views.generic import ListView
from inventory.models import SalesBooking
from inventory.mixins import AdminRequiredMixin


class SalesBookingsManagementView(AdminRequiredMixin, ListView):
    model = SalesBooking
    template_name = "inventory/admin_sales_bookings_management.html"
    context_object_name = "sales_bookings"
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('motorcycle', 'sales_profile').order_by("-created_at")
        search_term = self.request.GET.get("q", "").strip()

        if search_term:
            queryset = queryset.filter(
                Q(sales_booking_reference__icontains=search_term)
                | Q(customer_notes__icontains=search_term)
                | Q(motorcycle__brand__icontains=search_term)
                | Q(motorcycle__model__icontains=search_term)
                | Q(sales_profile__name__icontains=search_term)
                | Q(sales_profile__email__icontains=search_term)
                | Q(booking_status__icontains=search_term)
            ).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_term"] = self.request.GET.get("q", "")
        context["page_title"] = "Sales Bookings Management"
        return context
