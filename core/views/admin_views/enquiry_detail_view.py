from django.views.generic import DetailView
from core.models.enquiry import Enquiry
from core.mixins import AdminRequiredMixin

class EnquiryDetailView(AdminRequiredMixin, DetailView):
    model = Enquiry
    template_name = 'core/admin/enquiry_detail.html'
    context_object_name = 'enquiry'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Enquiry Details"
        ##

        return context
