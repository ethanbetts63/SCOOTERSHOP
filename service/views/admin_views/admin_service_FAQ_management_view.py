# service/views/admin_views/service_faq_management_view.py

from django.views.generic import ListView
from service.models import ServiceFAQ
from inventory.mixins import AdminRequiredMixin  # Assuming a shared mixin

class ServiceFAQManagementView(AdminRequiredMixin, ListView):
    """
    View for admin to manage (list) Service FAQs.
    """
    model = ServiceFAQ
    template_name = 'service/admin_service_FAQ_management.html'
    context_object_name = 'service_faqs'
    paginate_by = 15

    def get_queryset(self):
        """
        Orders the FAQs by booking step and then by their display order.
        This ordering is also defined in the model's Meta, but explicit here for clarity.
        """
        return ServiceFAQ.objects.all().order_by('booking_step', 'display_order')

    def get_context_data(self, **kwargs):
        """
        Adds the page title to the context.
        """
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Service FAQs Management"
        return context
