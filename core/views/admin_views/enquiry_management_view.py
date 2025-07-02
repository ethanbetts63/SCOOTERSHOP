from django.views.generic import ListView
from core.models.enquiry import Enquiry
from core.mixins import AdminRequiredMixin

class EnquiryManagementView(AdminRequiredMixin, ListView):
    model = Enquiry
    template_name = 'core/admin/enquiry_management.html'
    context_object_name = 'enquiries'
    paginate_by = 10


    def get_queryset(self):
        return Enquiry.objects.all().order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Enquiry Management"
        return context
