from django.views.generic import ListView
from inventory.models import SalesFAQ
from inventory.mixins import AdminRequiredMixin


class SalesFAQManagementView(AdminRequiredMixin, ListView):

    model = SalesFAQ
    template_name = "inventory/admin_sales_faq_management.html"
    context_object_name = "sales_faqs"
    paginate_by = 15

    def get_queryset(self):

        return SalesFAQ.objects.all().order_by("booking_step", "display_order")

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context["page_title"] = "Sales FAQs Management"
        return context
