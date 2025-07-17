from django.views.generic import ListView
from django.db.models import Count
from service.models import ServiceTerms
from service.mixins import AdminRequiredMixin


class ServiceTermsManagementView(AdminRequiredMixin, ListView):
    model = ServiceTerms
    template_name = "service/admin_service_terms_management.html"
    context_object_name = "terms_versions"
    paginate_by = 10

    def get_queryset(self):
        return ServiceTerms.objects.annotate(
            booking_count=Count("service_bookings")
        ).order_by("-version_number")

    def get_context_data(self, **kwargs):
        """
        Adds the page title to the context.
        """
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Service Terms & Conditions Management"
        return context
