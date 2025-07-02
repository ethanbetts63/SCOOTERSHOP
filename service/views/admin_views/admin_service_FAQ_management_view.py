                                                          

from django.views.generic import ListView
from service.models import ServiceFAQ
from inventory.mixins import AdminRequiredMixin                           

class ServiceFAQManagementView(AdminRequiredMixin, ListView):
    #--
    model = ServiceFAQ
    template_name = 'service/admin_service_FAQ_management.html'
    context_object_name = 'service_faqs'
    paginate_by = 15

    def get_queryset(self):
        #--
        return ServiceFAQ.objects.all().order_by('booking_step', 'display_order')

    def get_context_data(self, **kwargs):
        #--
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Service FAQs Management"
        return context
