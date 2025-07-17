from django.views.generic import ListView
from service.models import Servicefaq
from inventory.mixins import AdminRequiredMixin


class ServicefaqManagementView(AdminRequiredMixin, ListView):
    model = Servicefaq
    template_name = "service/admin_service_faq_management.html"
    context_object_name = "service_faqs"
    paginate_by = 15

    def get_queryset(self):
        return Servicefaq.objects.all().order_by("booking_step", "display_order")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Service faqs Management"
        return context
